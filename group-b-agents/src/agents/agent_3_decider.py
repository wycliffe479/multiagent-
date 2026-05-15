"""group-b-agents/src/agents/agent_3_decider.py
AGENT 3: Decision Maker
  Input : state["parsed_alert"], state["past_incidents"], state["recommended_fix"]
  Output: state["decision"], state["status"]
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from openai import OpenAI
from src.config import OPENCODE_API_KEY, OPENCODE_BASE_URL, MODEL_NAME

llm = OpenAI(api_key=OPENCODE_API_KEY, base_url=OPENCODE_BASE_URL)

_SYSTEM = "You are an SRE decision engine. Return ONLY valid JSON with no markdown fences."

_PROMPT = """You must decide the final remediation action for this incident.

CURRENT ALERT:
  Server   : {server_name}
  Error    : {error_type}
  Severity : {severity}
  Location : {location}

RECOMMENDED FIX (from historical data / LLM search):
  {recommended_fix}

PAST INCIDENTS (most recent first):
{past_incidents}

Decision rules:
  • severity = critical  AND known fix exists  → auto-execute the fix
  • severity = critical  AND no known fix      → escalate to human
  • severity = warning                         → auto-fix if confidence > 0.8, else monitor
  • severity = info                            → monitor / log only

Return ONLY a JSON object with these keys:
{{
  "action": "<one of: restart_server | rollback | escalate | monitor | create_ticket | scale_up | restart_pods | clear_cache>",
  "auto_execute": <true|false>,
  "reasoning": "<1–2 sentences explaining the choice>",
  "confidence": <0.0–1.0>,
  "estimated_recovery_minutes": <integer>
}}"""


def _clean_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    return text


_ALLOWED_ACTIONS = {
    "restart_server",
    "rollback",
    "escalate",
    "monitor",
    "create_ticket",
    "scale_up",
    "restart_pods",
    "clear_cache",
}


def _coerce_confidence(v: Any) -> float:
    try:
        f = float(v)
    except Exception:
        return 0.0
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


def _validate_decision(raw: Any, fallback: dict) -> dict:
    """Ensure the decision object matches the schema & allow-list."""
    if not isinstance(raw, dict):
        return fallback

    action = raw.get("action", fallback.get("action"))
    if action not in _ALLOWED_ACTIONS:
        action = "monitor"

    auto_execute = raw.get("auto_execute", fallback.get("auto_execute", False))
    # Coerce to bool conservatively
    if isinstance(auto_execute, str):
        auto_execute = auto_execute.strip().lower() in {"true", "1", "yes"}
    else:
        auto_execute = bool(auto_execute)

    reasoning = raw.get("reasoning", fallback.get("reasoning", ""))
    if not isinstance(reasoning, str):
        reasoning = str(reasoning)

    confidence = _coerce_confidence(raw.get("confidence", fallback.get("confidence", 0.0)))

    est = raw.get("estimated_recovery_minutes", fallback.get("estimated_recovery_minutes", 0))
    try:
        est = int(est)
    except Exception:
        est = int(fallback.get("estimated_recovery_minutes", 0) or 0)
    if est < 0:
        est = 0

    return {
        "action": action,
        "auto_execute": auto_execute,
        "reasoning": reasoning,
        "confidence": confidence,
        "estimated_recovery_minutes": est,
    }


def agent_3_decide_action(state: dict) -> dict:
    parsed          = state.get("parsed_alert", {})
    past_incidents  = state.get("past_incidents", [])
    recommended_fix = state.get("recommended_fix", "monitor")


    server = parsed.get("server_name", "unknown")
    print(f"[Agent 3] Deciding action for server: {server}")

    # Summarise past incidents compactly for the prompt
    past_summary = "\n".join(
        f"  - {inc.get('incident_id', inc.get('id', '?'))}: "
        f"error={inc.get('error_type', '?')}  fix={inc.get('fix_applied', inc.get('fix', '?'))}"
        for inc in past_incidents[:5]
    ) or "  (none)"

    fallback = {
        "action": "monitor",
        "auto_execute": False,
        "reasoning": "LLM rate-limited/unavailable; defaulting to safe monitor.",
        "confidence": 0.0,
        "estimated_recovery_minutes": 0,
    }

    try:
        response = llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": _PROMPT.format(
                    server_name     = parsed.get("server_name", "unknown"),
                    error_type      = parsed.get("error_type",  "unknown"),
                    severity        = parsed.get("severity",    "unknown"),
                    location        = parsed.get("location",    "unknown"),
                    recommended_fix = recommended_fix,
                    past_incidents  = past_summary,
                )},
            ],
            temperature=0.1,
        )

        content = _clean_json(response.choices[0].message.content)

        try:
            raw_decision = json.loads(content)
        except json.JSONDecodeError:
            print(f"[Agent 3] WARNING: JSON parse failed. Raw: {content[:120]}")
            raw_decision = None

        decision = _validate_decision(raw_decision, fallback)

    except Exception as exc:
        # Infallibility: never crash pipeline on LLM errors (429/free quota, auth, network, etc.)
        print(f"[Agent 3] WARNING: LLM call failed ({exc}); using safe fallback decision.")
        decision = fallback





    print(
        f"[Agent 3] ✓ Action={decision.get('action')}  auto_execute={decision.get('auto_execute')}  confidence={decision.get('confidence')}"
    )
    return {"decision": decision, "status": "decided"}

