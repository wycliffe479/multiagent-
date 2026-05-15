"""group-b-agents/src/workflow/graph.py
Wires Agent 3 and Agent 4 into a LangGraph StateGraph.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from langgraph.graph import StateGraph, END
from src.workflow.state import ActionState
from src.agents.agent_3_decider  import agent_3_decide_action
from src.agents.agent_4_notifier import agent_4_notify_slack


def build_workflow():
    graph = StateGraph(ActionState)

    graph.add_node("decide_action", agent_3_decide_action)
    graph.add_node("notify_slack",  agent_4_notify_slack)

    graph.set_entry_point("decide_action")
    graph.add_edge("decide_action", "notify_slack")
    graph.add_edge("notify_slack",  END)

    return graph.compile()


workflow = build_workflow()
