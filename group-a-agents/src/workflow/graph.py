"""group-a-agents/src/workflow/graph.py
Wires Agent 1 and Agent 2 into a LangGraph StateGraph.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from langgraph.graph import StateGraph, END
from src.workflow.state import AlertState
from src.agents.agent_1_reader   import agent_1_read_alert
from src.agents.agent_2_searcher import agent_2_search_past


def build_workflow():
    graph = StateGraph(AlertState)

    graph.add_node("read_alert", agent_1_read_alert)
    graph.add_node("search_past", agent_2_search_past)


    graph.set_entry_point("read_alert")

    def _route_after_parse(state: AlertState):
        # Short-circuit for invalid/unreliable parses.
        if not state.get("parse_ok", False):
            return END
        return "search_past"

    graph.add_conditional_edges("read_alert", _route_after_parse)
    graph.add_edge("search_past", END)



    return graph.compile()


workflow = build_workflow()
