"""
Generation Agent
=================
Synthesizes verified research and blueprint requirements into a comprehensive report.
Incorporates specific feedback and critique points during revision passes.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from agents.state import AgentState
from agents.prompts import WRITER_PROMPT
from agents.utils import to_text


def generation_node(state: AgentState, model) -> dict:
    """Generate the initial draft or revise an existing draft using new research and critique.

    Args:
        state: Current agent state with task, plan, content, and critique.
        model: LLM for report generation.

    Returns:
        State update with draft, updated revision_number, and synthesis reasoning.
    """
    content = "\n\n".join(state.get('content') or [])
    plan_text = to_text(state.get('plan', ''))
    task_text = to_text(state.get('task', ''))
    critique_text = to_text(state.get('critique', ''))
    curr_rev = state.get("revision_number", 1)

    prompt_context = f"Topic/Goal:\n{task_text}\n\nBlueprint Structure:\n{plan_text}"
    if critique_text and curr_rev > 1:
        prompt_context += f"\n\nPRIOR CRITIQUE TO RESOLVE:\n{critique_text}\n\nMake sure to explicitly address every issue mentioned above."

    messages = [
        SystemMessage(content=WRITER_PROMPT.format(content=content)),
        HumanMessage(content=prompt_context)
    ]

    response = model.invoke(messages)
    draft_text = to_text(response.content)

    reasoning_summary = (
        f"Synthesized {len(state.get('content', []))} research findings into Draft v{curr_rev}."
        if curr_rev == 1 else
        f"Revised draft to version {curr_rev}, incorporating Reflection feedback and deepening evidence."
    )

    return {
        "draft": draft_text,
        "revision_number": curr_rev + 1,
        "agent_reasoning": {
            "agent": "generate",
            "title": f"Synthesis & Draft Construction (v{curr_rev})",
            "summary": reasoning_summary,
            "revision": curr_rev
        }
    }
