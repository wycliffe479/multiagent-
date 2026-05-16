"""group-b-agents/src/agents/agent_3_decider.py
AGENT 3: Decision Maker
  Input : state["parsed_alert"], state["past_incidents"], state["recommended_fix"]
  Output: state["decision"], state["status"]
"""

import json
import sys
import os
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from openai import OpenAI


def _get_llm():
    from src.config import OPENCODE_API_KEY, OPENCODE_BASE_URL, MODEL_NAME
    return OpenAI(api_key=OPENCODE_API_KEY, base_url=OPENCODE_BASE_URL), MODEL_NAME

_SYSTEM = "You are a senior SRE decision engine. Think step by step before deciding."

_DECOMPOSE_PROMPT = """Analyze this incident and break it down:

ALERT:
  Server   : {server_name}
  Error    : {error_type}
  Severity : {severity}
  Location : {location}
  Recommended fix (from history/web): {recommended_fix}
  Past incidents: {past_incidents}

Answer these 3 questions in plain text:
1. ROOT CAUSE: What is most likely causing this error?
2. BLAST RADIUS: What systems/users are affected and how badly?
3. OPTIONS: List 2-3 possible remediation actions with one-line pros/cons each."""

_PLAN_PROMPT = """Given this incident analysis:
{decomposition}

And these decision rules:
  • severity=critical AND known fix exists → auto-execute the fix
  • severity=critical AND no known fix    → escalate to human
  • severity=warning                      → auto-fix if confidence > 0.8, else monitor
  • severity=info                         → monitor only

Pick the single best action from:
  restart_server | rollback | escalate | monitor | create_ticket | scale_up | restart_pods | clear_cache

Respond in plain text:
CHOSEN ACTION: <action>
REASON: <one sentence>
CONFIDENCE: <0.0-1.0>
AUTO EXECUTE: <yes/no>
RECOVERY MINUTES: <integer>"""

_REFLECT_PROMPT = """You chose this plan:
{plan}

For this incident:
  Server: {server_name} | Error: {error_type} | Severity: {severity}

Critically review: Is this the safest, most effective action?
If yes, confirm it. If not, correct it.

Then return ONLY a JSON object (no markdown):
{{
  "action": "<action>",
  "auto_execute": <true|false>,
  "reasoning": "<1-2 sentences combining your analysis and why this is the best choice>",
  "confidence": <0.0-1.0>,
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
        llm, MODEL_NAME = _get_llm()

        ctx = dict(
            server_name     = parsed.get("server_name", "unknown"),
            error_type      = parsed.get("error_type",  "unknown"),
            severity        = parsed.get("severity",    "unknown"),
            location        = parsed.get("location",    "unknown"),
            recommended_fix = recommended_fix,
            past_incidents  = past_summary,
        )

        # --- Step 1: Decompose ---
        print(f"[Agent 3] Step 1/3 — Decomposing incident …")
        r1 = llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": _DECOMPOSE_PROMPT.format(**ctx)},
            ],
            temperature=0.2,
        )
        decomposition = r1.choices[0].message.content.strip()
        print(f"[Agent 3] Decomposition:\n{decomposition}")

        # --- Step 2: Plan ---
        print(f"[Agent 3] Step 2/3 — Planning remediation …")
        r2 = llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": _PLAN_PROMPT.format(decomposition=decomposition)},
            ],
            temperature=0.1,
        )
        plan = r2.choices[0].message.content.strip()
        print(f"[Agent 3] Plan:\n{plan}")

        # --- Step 3: Reflect & output JSON ---
        print(f"[Agent 3] Step 3/3 — Reflecting and finalizing …")
        r3 = llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": _REFLECT_PROMPT.format(
                    plan=plan,
                    server_name=ctx["server_name"],
                    error_type=ctx["error_type"],
                    severity=ctx["severity"],
                )},
            ],
            temperature=0.0,
        )
        content = _clean_json(r3.choices[0].message.content)

        try:
            raw_decision = json.loads(content)
        except json.JSONDecodeError:
            print(f"[Agent 3] WARNING: JSON parse failed on reflect step. Raw: {content[:120]}")
            raw_decision = None

        decision = _validate_decision(raw_decision, fallback)

    except Exception as exc:
        print(f"[Agent 3] WARNING: LLM call failed ({exc}); using safe fallback decision.")
        decision = fallback

    print(
        f"[Agent 3] ✓ Action={decision.get('action')}  auto_execute={decision.get('auto_execute')}  confidence={decision.get('confidence')}"
    )
    return {"decision": decision, "status": "decided"}