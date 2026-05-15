"""group-a-agents/main.py — run Group A standalone."""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))   # make src/ importable

from src.workflow.graph import workflow

TEST_ALERT = (
    "ALERT: server-7 is down at us-east-1. "
    "Error: connection_refused. Severity: critical. "
    "Time: 2026-05-15T03:00:00Z"
)

if __name__ == "__main__":
    initial_state = {
        "raw_alert":      TEST_ALERT,
        "parsed_alert":   {},
        "past_incidents": [],
        "recommended_fix": "",
        "reasoning":       "",
        "status":          "",
    }

    print("=" * 60)
    print("GROUP A — Alert Reader + Past Incident Searcher")
    print("=" * 60)

    result = workflow.invoke(initial_state)

    print("\n" + "=" * 60)
    print("GROUP A RESULT")
    print("=" * 60)
    print(f"Parsed alert  : {result.get('parsed_alert')}")
    print(f"Past incidents: {len(result.get('past_incidents', []))} found")
    print(f"Recommended   : {result.get('recommended_fix')}")
    print(f"Reasoning     : {result.get('reasoning')}")
    print(f"Status        : {result.get('status')}")
