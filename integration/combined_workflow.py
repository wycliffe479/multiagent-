"""integration/combined_workflow.py
Runs all four agents in sequence: A1 → A2 → A3 → A4.
This is the full end-to-end pipeline.
"""

import sys, os

# Make both group dirs importable as top-level packages
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# We import the compiled LangGraph workflows from each group and chain them manually.
# (Alternatively you could build a single mega-graph — this approach keeps groups independent.)

import importlib.util

def _load_workflow(rel_path: str):
    """Import a workflow module by relative path and return its `workflow` object.

    Uses standard package import (not exec_module) to avoid `src` package collisions
    across group-a/src and group-b/src.
    """
    abs_path = os.path.join(_ROOT, rel_path)

    # Determine group root (e.g. .../group-a-agents)
    if "group-a-agents" in abs_path:
        group_root = os.path.join(_ROOT, "group-a-agents")
        src_dir = os.path.join(group_root, "src")
    elif "group-b-agents" in abs_path:
        group_root = os.path.join(_ROOT, "group-b-agents")
        src_dir = os.path.join(group_root, "src")
    else:
        raise RuntimeError(f"Cannot determine group from path: {abs_path}")



    # Prevent `src.*` from bleeding across group loads.
    for k in list(sys.modules.keys()):
        if k == "src" or k.startswith("src."):
            sys.modules.pop(k, None)

    old_sys_path = sys.path[:]
    try:
        # Remove both groups' src roots from sys.path, then add only the selected one.
        other_a_src = os.path.join(_ROOT, "group-a-agents", "src")
        other_b_src = os.path.join(_ROOT, "group-b-agents", "src")
        sys.path[:] = [p for p in sys.path if p not in (other_a_src, other_b_src)]

        for p in (_ROOT, group_root, src_dir):
            if p not in sys.path:
                sys.path.insert(0, p)

        # graph.py lives at src/workflow/graph.py
        module = __import__("src.workflow.graph", fromlist=["workflow"])
        return getattr(module, "workflow")
    finally:
        sys.path[:] = old_sys_path





def run_full_pipeline(raw_alert: str) -> dict:
    """Run the complete 4-agent pipeline and return the final state."""

    print("\n" + "=" * 60)
    print("ANVIL 2026 — Full Pipeline")
    print("=" * 60)

    # ----- Group A -----
    workflow_a = _load_workflow("group-a-agents/src/workflow/graph.py")
    state_a = workflow_a.invoke({
        "raw_alert":       raw_alert,
        "parsed_alert":    {},
        "past_incidents":  [],
        "recommended_fix": "",
        "reasoning":       "",
        "status":          "",
    })

    # ----- Group B (feeds on Group A output) -----
    workflow_b = _load_workflow("group-b-agents/src/workflow/graph.py")
    state_b = workflow_b.invoke({
        "parsed_alert":    state_a.get("parsed_alert",    {}),
        "past_incidents":  state_a.get("past_incidents",  []),
        "recommended_fix": state_a.get("recommended_fix", "monitor"),
        "reasoning":       state_a.get("reasoning",       ""),
        "decision":        {},
        "slack_message":   "",
        "slack_status":    "",
        "status":          "",
    })

    # Merge both states for convenience
    final = {**state_a, **state_b}

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Server       : {final.get('parsed_alert', {}).get('server_name')}")
    print(f"  Error type   : {final.get('parsed_alert', {}).get('error_type')}")
    print(f"  Severity     : {final.get('parsed_alert', {}).get('severity')}")
    print(f"  Recommended  : {final.get('recommended_fix')}")
    print(f"  Decision     : {final.get('decision', {}).get('action')}")
    print(f"  Auto-execute : {final.get('decision', {}).get('auto_execute')}")
    print(f"  Slack status : {final.get('slack_status')}")
    print(f"  Status       : {final.get('status')}")

    return final


if __name__ == "__main__":
    TEST_ALERT = (
        "ALERT: server-7 is down at us-east-1. "
        "Error: connection_refused. Severity: critical. "
        "Time: 2026-05-15T03:00:00Z"
    )
    run_full_pipeline(TEST_ALERT)
