"""group-a-agents/src/workflow/state.py
Shared state schema that flows through the Group A LangGraph pipeline.
"""

from typing import TypedDict, Any


class AlertState(TypedDict, total=False):
    # Input
    raw_alert: str

    # Agent 1 output
    parsed_alert: dict[str, Any]
    normalized_alert: dict[str, Any]

    # Agent 1 validation
    parse_ok: bool
    parse_errors: list[str]

    # Agent 2 output
    past_incidents: list[dict[str, Any]]
    recommended_fix: str
    reasoning: str
    source: str
    logs: list[str]

    # Pipeline control
    status: str

