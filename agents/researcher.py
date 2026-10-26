"""
Research Plan Agent
====================
Autonomous research agent that reasons about information gaps in the blueprint,
decides targeted search strategies, executes live web queries, and logs tool calls.
"""

import json
from langchain_core.messages import SystemMessage, HumanMessage
from agents.state import AgentState
from agents.prompts import RESEARCHER_DECISION_PROMPT
from agents.utils import to_text


def research_plan_node(state: AgentState, model, tavily) -> dict:
    """Analyze blueprint gaps, autonomously decide web search queries, and gather evidence.

    Args:
        state: Current agent state with task and plan.
        model: LLM for autonomous reasoning and query planning.
        tavily: TavilyClient for live search execution.

    Returns:
        State updates containing research content, tool call history, and reasoning traces.
    """
    task_text = state['task']
    if isinstance(task_text, list):
        task_text = " ".join(str(x) for x in task_text)

    prompt = RESEARCHER_DECISION_PROMPT.format(
        task=task_text,
        plan=state.get('plan', '')[:2000]
    )

    thought_process = "Analyzing report blueprint to identify required metrics, dates, and authoritative sources."
    queries = [f"{task_text} latest statistics", f"{task_text} facts and data"]

    try:
        response = model.invoke([
            SystemMessage(content="You are an autonomous research agent. Always reply in valid JSON."),
            HumanMessage(content=prompt)
        ])
        raw_text = to_text(response.content).strip()
        # Clean potential markdown fences
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        data = json.loads(raw_text)
        if isinstance(data, dict):
            thought_process = data.get("thought_process", thought_process)
            queries = data.get("queries", queries)
    except Exception as e:
        print(f"Researcher reasoning parse notice: {e}")
        # Fallback queries based on task
        queries = [
            f"{task_text} latest data facts",
            f"{task_text} analysis report"
        ]

    content = list(state.get('content') or [])
    tool_calls_log = list(state.get('tool_calls_log') or [])
    new_tool_calls = []

    for q in queries:
        call_record = {
            "agent": "research_plan",
            "tool": "web_search",
            "query": q,
            "status": "executing",
            "sources": []
        }
        try:
            res = tavily.search(query=q, max_results=3)
            found_sources = []
            for r in res.get('results', []):
                snippet = r.get('content', '')
                url = r.get('url', '')
                title = r.get('title', 'Web Result')
                if snippet:
                    content.append(f"[{title}] ({url}): {snippet}")
                if url:
                    found_sources.append({"title": title, "url": url})
            call_record["status"] = "success"
            call_record["sources"] = found_sources[:3]
            call_record["results_count"] = len(res.get('results', []))
        except Exception as e:
            call_record["status"] = f"error: {e}"
            call_record["results_count"] = 0

        tool_calls_log.append(call_record)
        new_tool_calls.append(call_record)

    return {
        "content": content,
        "tool_calls_log": tool_calls_log,
        "agent_reasoning": {
            "agent": "research_plan",
            "title": "Evidence Acquisition & Fact-Gathering",
            "summary": thought_process[:250] + ("..." if len(thought_process) > 250 else ""),
            "full_thought": thought_process,
            "queries_executed": queries,
            "tools_called": len(new_tool_calls)
        }
    }
