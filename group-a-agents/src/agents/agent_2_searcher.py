"""group-a-agents/src/agents/agent_2_searcher.py
AGENT 2: Past Incident Searcher
  1. Queries the local SQLite database for matching past incidents.
  2. If no DB match, falls back to an LLM-based recommendation.

  Input : state["parsed_alert"]
  Output: state["past_incidents"], state["recommended_fix"],
          state["reasoning"], state["source"], state["logs"], state["status"]
"""

import sys
import os

# Ensure project root and database/ are importable
_HERE        = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_DB_DIR       = os.path.join(_PROJECT_ROOT, "database")

for _p in (_PROJECT_ROOT, _DB_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from openai import OpenAI
from src.config import OPENCODE_API_KEY, OPENCODE_BASE_URL, MODEL_NAME
from database.db_manager import search_past_incidents, get_solution_for_error

llm = OpenAI(api_key=OPENCODE_API_KEY, base_url=OPENCODE_BASE_URL)

_SYSTEM = "You are an SRE expert. Suggest the single best remediation action."

_ALLOWED_ACTIONS = {
    "restart_server",
    "scale_up",
    "restart_pods",
    "clear_cache",
    "rollback",
    "escalate",
    "create_ticket",
    "monitor",
}

_PROMPT = """A server is experiencing the following error:

  Server     : {server_name}
  Error type : {error_type}
  Severity   : {severity}
  Location   : {location}

No historical fix was found in our database.

Return ONLY one of these action names (exactly as written, nothing else):
  restart_server | scale_up | restart_pods | clear_cache | rollback | escalate | create_ticket | monitor"""



def agent_2_search_past(state: dict) -> dict:
    logs: list[str] = []

    def log(msg: str):
        logs.append(msg)
        print(f"[Agent 2] {msg}")

    # If Agent 1 failed validation, return deterministic safe output.
    if not state.get("parse_ok", False):
        parse_errors = state.get("parse_errors", [])
        log(f"Skipping search_past: parse_ok=false; errors={parse_errors}")
        return {
            "past_incidents": [],
            "recommended_fix": "monitor",
            "reasoning":       "Agent 1 failed to parse/validate the alert; using safe monitoring action.",
            "source":          "parse_failed",
            "logs":            logs,
            "status":          "skipped",
        }

    parsed      = state.get("parsed_alert", {})
    server_name = parsed.get("server_name", "")
    error_type  = parsed.get("error_type",  "")
    severity    = parsed.get("severity",    "info")
    location    = parsed.get("location",    "")

    if not server_name or not error_type or error_type == "unknown":
        log("Unknown/empty parsed fields; forcing monitor")
        return {
            "past_incidents": [],
            "recommended_fix": "monitor",
            "reasoning":       "Alert fields were unknown/empty; using safe monitoring action.",
            "source":          "unknown_fields",
            "logs":            logs,
            "status":          "skipped",
        }

    log(f"Searching for: server={server_name!r}  error={error_type!r}")


    # ------------------------------------------------------------------
    # Step 1 — local database
    # ------------------------------------------------------------------
    log("Checking SQLite database for past incidents …")

    # Prefer error_type matches for semantic consistency; only use server_name as a fallback.
    local_incidents = search_past_incidents(server_name, error_type)
    if not local_incidents:
        local_incidents = search_past_incidents(server_name, "")


    if local_incidents:
        log(f"Found {len(local_incidents)} past incident(s) in database.")
        for inc in local_incidents:
            log(f"  › {inc['incident_id']}: {inc['error_type']} → fix={inc['fix_applied']}")

        solution = get_solution_for_error(error_type)
        if solution:
            recommended_fix = solution["fix"]
            log(f"Known solution: {recommended_fix!r}  (success rate {solution['success_rate']*100:.0f}%)")
            source = "database"
        else:
            recommended_fix = local_incidents[0]["fix_applied"]
            log(f"No exact solution entry; using most-recent fix: {recommended_fix!r}")
            source = "database_similar"

        past_incidents = local_incidents

    else:
        # ------------------------------------------------------------------
        # Step 2 — LLM fallback
        # ------------------------------------------------------------------
        log("No database match. Asking LLM for recommendation …")
        try:
            response = llm.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user",   "content": _PROMPT.format(
                        server_name=server_name,
                        error_type=error_type,
                        severity=severity,
                        location=location,
                    )},
                ],
                temperature=0.1,
            )
            raw = response.choices[0].message.content.strip()
            # Extract only exact action token; reject anything else.
            cand = raw.strip().strip(".,;:!?").split()[0] if raw else ""
            if cand not in _ALLOWED_ACTIONS:
                log(f"LLM returned invalid action {raw!r}; forcing monitor")
                recommended_fix = "monitor"
                past_incidents = [{"source": "llm_fallback", "suggested_fix": raw, "forced": True}]
                source = "llm_fallback_invalid"
            else:
                recommended_fix = cand
                log(f"LLM suggests: {recommended_fix!r}")
                past_incidents = [{"source": "llm_fallback", "suggested_fix": recommended_fix}]
                source = "llm_fallback"

        except Exception as exc:
            log(f"LLM call failed: {exc}")
            recommended_fix = "monitor"
            past_incidents  = [{"source": "fallback", "note": "No solution found"}]
            source          = "fallback"


    # Hard safety: never output an action outside the allow-list.
    if recommended_fix not in _ALLOWED_ACTIONS:
        log(f"WARNING: Non-allow-listed recommended_fix={recommended_fix!r}; forcing monitor")
        recommended_fix = "monitor"
        source = "safety_forced"

    log(f"✓ Recommended fix: {recommended_fix!r}  (source: {source})")

    return {
        "past_incidents":  past_incidents,
        "recommended_fix": recommended_fix,
        "reasoning":       f"Fix determined from {source}",
        "source":          source,
        "logs":            logs,
        "status":          "searched",
    }

