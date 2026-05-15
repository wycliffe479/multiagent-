"""group-a-agents/src/agents/agent_1_reader.py
AGENT 1: Alert Reader
  Input : state["raw_alert"]  (plain-text alert string)
  Output: state["parsed_alert"] (structured dict), state["status"]
"""

import json
import sys
import os

# Make sure the project root is on the path so src.config resolves
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from openai import OpenAI
from src.config import OPENCODE_API_KEY, OPENCODE_BASE_URL, MODEL_NAME

llm = OpenAI(api_key=OPENCODE_API_KEY, base_url=OPENCODE_BASE_URL)

_SYSTEM = "You are an alert parser. Return ONLY valid JSON with no extra text."

_PROMPT = """Parse this alert and extract the following fields.

ALERT:
{raw_alert}

Return ONLY a JSON object with these keys:
- server_name   : which server is affected
- error_type    : type of error (e.g. down, high_cpu, memory_leak, connection_refused, disk_full, deployment_failed)
- location      : geographic region (e.g. us-east-1)
- severity      : "critical", "warning", or "info"
- timestamp     : when it happened (ISO-8601 or human-readable)

Return ONLY valid JSON. No markdown fences, no explanation."""


def _clean_json(raw: str) -> str:
    """Strip markdown fences if the model wrapped its answer."""
    # Defensive: some SDK responses may return None for content.
    if raw is None:
        return ""
    text = str(raw).strip()
    if text.startswith("```"):
        parts = text.split("```")
        # parts[1] is the content inside the fences
        text = parts[1].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    return text



def _extract_from_raw(raw_alert: str) -> dict[str, str]:
    """Deterministically extract key fields from the raw alert string."""
    import re

    out: dict[str, str] = {}

    m = re.search(r"Severity\s*:\s*(critical|warning|info)\b", raw_alert, re.IGNORECASE)
    if m:
        out["severity"] = m.group(1).lower()

    m = re.search(r"Error\s*:\s*([A-Za-z0-9_\-]+)", raw_alert)
    if m:
        out["error_type"] = m.group(1).strip().lower()

    # server-7 format from: server-7 ...
    m = re.search(r"server\s*-\s*([A-Za-z0-9_\-]+)", raw_alert, re.IGNORECASE)
    if m:
        server_id = m.group(1).strip()
        if server_id:
            out["server_name"] = f"server-{server_id}".lower()

    # us-east-1 format from: at us-east-1
    m = re.search(r"at\s+([a-z]{2}-[a-z]+-\d+)", raw_alert, re.IGNORECASE)
    if m:
        out["location"] = m.group(1).lower()

    return out


def agent_1_read_alert(state: dict) -> dict:
    raw_alert = state.get("raw_alert", "")
    print(f"[Agent 1] Reading alert: {raw_alert[:80]}...")

    # Deterministic baseline from raw alert (infallibility source of truth)
    recovered = _extract_from_raw(raw_alert)

    try:
        response = llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": _PROMPT.format(raw_alert=raw_alert)},
            ],
            temperature=0.1,
        )
        content = _clean_json(getattr(response.choices[0].message, "content", None))

        try:
            parsed = json.loads(content)
            # Defensive: enforce dict shape early.
            if not isinstance(parsed, dict):
                raise json.JSONDecodeError("LLM parsed non-dict", content, 0)
        except Exception:
            print(f"[Agent 1] WARNING: Could not parse/validate LLM response; using deterministic raw fallback. Raw: {content[:120]}")
            parsed = {
                "server_name": recovered.get("server_name", "unknown"),
                "error_type":  recovered.get("error_type",  "unknown"),
                "location":    recovered.get("location",    "unknown"),
                "severity":    recovered.get("severity",    "info"),
                "timestamp":   "unknown",
            }

    except Exception as exc:
        # Infallibility: never let transient LLM issues (auth/rate-limit/network) break the pipeline.
        print(f"[Agent 1] WARNING: LLM call failed ({exc}); using deterministic raw fallback.")
        parsed = {
            "server_name": recovered.get("server_name", "unknown"),
            "error_type":  recovered.get("error_type",  "unknown"),
            "location":    recovered.get("location",    "unknown"),
            "severity":    recovered.get("severity",    "info"),
            "timestamp":   "unknown",
        }



    # Canonical normalization (so casing drift doesn't break infallibility)
    if isinstance(parsed.get("severity"), str):
        parsed["severity"] = parsed["severity"].strip().lower()
    if isinstance(parsed.get("error_type"), str):
        parsed["error_type"] = parsed["error_type"].strip().lower()
    if isinstance(parsed.get("server_name"), str):
        parsed["server_name"] = parsed["server_name"].strip().lower()
    if isinstance(parsed.get("location"), str):
        parsed["location"] = parsed["location"].strip().lower()

    # If LLM returned missing/empty/unknown fields, override from deterministic extraction
    if parsed.get("server_name") in (None, "", "unknown") and recovered.get("server_name"):
        parsed["server_name"] = recovered["server_name"]
    if parsed.get("error_type") in (None, "", "unknown") and recovered.get("error_type"):
        parsed["error_type"] = recovered["error_type"]
    if parsed.get("location") in (None, "", "unknown") and recovered.get("location"):
        parsed["location"] = recovered["location"]
    if parsed.get("severity") not in {"critical", "warning", "info"} and recovered.get("severity"):
        parsed["severity"] = recovered["severity"]

    # Final hard defaults
    parsed.setdefault("server_name", "unknown")
    parsed.setdefault("error_type", "unknown")
    parsed.setdefault("location", "unknown")
    parsed.setdefault("severity", "info")
    parsed.setdefault("timestamp", "unknown")


    print(
        f"[Agent 1] ✓ Parsed → server={parsed.get('server_name')} "
        f"error={parsed.get('error_type')} severity={parsed.get('severity')}"
    )
    # Validation + normalization status for downstream infallibility.
    parse_errors: list[str] = []

    severity = parsed.get("severity", "info")
    if severity not in {"critical", "warning", "info"}:
        parse_errors.append(f"Invalid severity: {severity!r}")

    error_type = parsed.get("error_type", "unknown")
    if not error_type or not isinstance(error_type, str) or error_type == "unknown":
        parse_errors.append("Unknown error_type")

    server_name = parsed.get("server_name", "unknown")
    if not server_name or not isinstance(server_name, str):
        parse_errors.append("Invalid server_name")

    location = parsed.get("location", "unknown")
    if not location or not isinstance(location, str):
        parse_errors.append("Invalid location")

    parse_ok = len(parse_errors) == 0

    # normalized_alert is what Agent 2 should trust.
    normalized_alert = {
        "server_name": parsed.get("server_name", "unknown"),
        "error_type": parsed.get("error_type", "unknown"),
        "location": parsed.get("location", "unknown"),
        # Canonical severity fallback
        "severity": parsed.get("severity", "info") if parsed.get("severity") in {"critical","warning","info"} else "info",
        "timestamp": parsed.get("timestamp", "unknown"),
    }

    # Hard guarantee: even if parse_ok=false, keep normalized_alert canonical/usable.
    if not normalized_alert.get("error_type") or normalized_alert.get("error_type") == "unknown":
        normalized_alert["error_type"] = "unknown"
    if not normalized_alert.get("server_name") or normalized_alert.get("server_name") == "unknown":
        normalized_alert["server_name"] = "unknown"
    if not normalized_alert.get("location") or normalized_alert.get("location") == "unknown":
        normalized_alert["location"] = "unknown"


    return {
        "parsed_alert": parsed,
        "normalized_alert": normalized_alert,
        "parse_ok": parse_ok,
        "parse_errors": parse_errors,
        "status": "parsed",
    }



