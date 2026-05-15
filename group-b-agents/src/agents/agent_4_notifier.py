"""group-b-agents/src/agents/agent_4_notifier.py
AGENT 4: Slack Notifier
  Input : state["parsed_alert"], state["decision"]
  Output: state["slack_message"], state["slack_status"], state["status"]
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import requests
from src.config import SLACK_WEBHOOK_URL


def agent_4_notify_slack(state: dict) -> dict:
    parsed   = state.get("parsed_alert", {})
    decision = state.get("decision", {})

    server    = parsed.get("server_name", "unknown")
    severity  = parsed.get("severity",    "info")
    error     = parsed.get("error_type",  "unknown")
    location  = parsed.get("location",    "unknown")

    action    = decision.get("action",                     "unknown")
    reasoning = decision.get("reasoning",                  "")
    recovery  = decision.get("estimated_recovery_minutes", 0)
    auto_exec = decision.get("auto_execute",               False)
    confidence = decision.get("confidence", 0.0)
    # Coerce to float for formatting safety
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0
    if confidence < 0.0:
        confidence = 0.0
    if confidence > 1.0:
        confidence = 1.0


    print(f"[Agent 4] Preparing Slack notification for: {server} → {action}")

    severity_emoji = (
        ":red_circle:"    if severity == "critical" else
        ":yellow_circle:" if severity == "warning"  else
        ":blue_circle:"
    )
    auto_label = "Yes :white_check_mark:" if auto_exec else "No — manual intervention required"

    message = f"""{severity_emoji} *INCIDENT ALERT: {server}*

*Details*
• Error      : `{error}`
• Location   : {location}
• Severity   : *{severity.upper()}*

*AI Decision*
• Action     : `{action}`
• Auto-execute: {auto_label}
• Confidence : {confidence * 100:.0f}%
• Reasoning  : {reasoning[:200]}
• Est. recovery: ~{recovery} min

:robot_face: _Handled autonomously by Anvil 2026 Agent Pipeline_"""

    # ----------------------------------------------------------------
    # Send to Slack (or fall back to console)
    # ----------------------------------------------------------------
    slack_status: str
    # Attempt send whenever a webhook URL is configured; be tolerant of proxies/format.
    if SLACK_WEBHOOK_URL:

        try:
            resp = requests.post(
                SLACK_WEBHOOK_URL,
                json={"text": message},
                timeout=10,
            )
            if resp.status_code == 200:
                print("[Agent 4] ✓ Slack notification sent.")
                slack_status = "sent"
            else:
                print(f"[Agent 4] Slack returned HTTP {resp.status_code}: {resp.text[:80]}")
                slack_status = "failed"
        except Exception as exc:
            print(f"[Agent 4] Slack request raised: {exc}")
            slack_status = "error"
    else:
        print("[Agent 4] No Slack webhook configured — printing message:\n")
        print(message)
        slack_status = "no_webhook"

    return {
        "slack_message": message,
        "slack_status":  slack_status,
        "status":        "completed",
    }
