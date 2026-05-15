"""group-b-agents/src/workflow/state.py
Shared state schema that flows through the Group B LangGraph pipeline.
"""

from typing import TypedDict, Any


class ActionState(TypedDict, total=False):
    # Comes from Group A (or test harness)
    parsed_alert: dict[str, Any]
    past_incidents: list[dict[str, Any]]
    recommended_fix: str
    reasoning: str

    # Agent 3 output
    decision: dict[str, Any]

    # Agent 4 output
    slack_message: str
    slack_status: str

    # Pipeline control
    status: str
