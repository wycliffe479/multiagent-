"""group-b-agents/main.py — run Group B standalone."""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.workflow.graph import workflow

# Simulate data that would arrive from Group A
TEST_INPUT = {
    "parsed_alert": {
        "server_name": "server-7",
        "error_type":  "connection_refused",
        "severity":    "critical",
        "location":    "us-east-1",
        "timestamp":   "2026-05-15T03:00:00Z",
    },
    "past_incidents": [
        {"incident_id": "INC-047", "error_type": "connection_refused", "fix_applied": "restart_server", "created_at": "2026-04-10"},
        {"incident_id": "INC-023", "error_type": "connection_refused", "fix_applied": "restart_server", "created_at": "2026-03-15"},
    ],
    "recommended_fix": "restart_server",
    "reasoning":       "Matches past incident pattern",
    "decision":        {},
    "slack_message":   "",
    "slack_status":    "",
    "status":          "",
}

if __name__ == "__main__":
    print("=" * 60)
    print("GROUP B — Decision Maker + Slack Notifier")
    print("=" * 60)

    result = workflow.invoke(TEST_INPUT)

    print("\n" + "=" * 60)
    print("GROUP B RESULT")
    print("=" * 60)
    dec = result.get("decision", {})
    print(f"Action        : {dec.get('action')}")
    print(f"Auto-execute  : {dec.get('auto_execute')}")
    print(f"Confidence    : {dec.get('confidence')}")
    print(f"Slack status  : {result.get('slack_status')}")
    print(f"Final status  : {result.get('status')}")
