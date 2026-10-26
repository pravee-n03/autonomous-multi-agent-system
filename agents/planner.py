"""
Planning Agent
===============
Analyzes the user's objective and creates an architectural report blueprint
along with transparent strategic reasoning.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from agents.state import AgentState
from agents.prompts import PLAN_PROMPT
from agents.utils import to_text


def plan_node(state: AgentState, model) -> dict:
    """Generate a structured blueprint and strategic reasoning for the report.

    Args:
        state: Current agent state containing the task.
        model: The LLM instance to use.

    Returns:
        State update dictionary containing plan, reasoning, and tool log initialization.
    """
    messages = [
        SystemMessage(content=PLAN_PROMPT),
        HumanMessage(content=f"Create a strategic blueprint for this report request:\n\n{state['task']}")
    ]
    response = model.invoke(messages)
    plan_text = to_text(response.content)

    # Separate strategy thoughts from blueprint if present
    reasoning_summary = "Formulated research strategy, section boundaries, and target metrics."
    if "### THOUGHT PROCESS" in plan_text:
        parts = plan_text.split("### REPORT BLUEPRINT")
        if len(parts) > 1:
            reasoning_summary = parts[0].replace("### THOUGHT PROCESS & STRATEGY", "").strip()

    return {
        "plan": plan_text,
        "agent_reasoning": {
            "agent": "planner",
            "title": "Strategy & Blueprint Formulation",
            "summary": reasoning_summary[:300] + ("..." if len(reasoning_summary) > 300 else ""),
            "full_thought": reasoning_summary
        },
        "tool_calls_log": state.get("tool_calls_log") or []
    }
