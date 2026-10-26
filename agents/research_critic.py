"""
Research Critique Agent
========================
Autonomous targeted research agent that analyzes specific gaps highlighted by
the Reflection Agent, performs surgical web queries, and accumulates deep evidence
for the subsequent revision.
"""

import json
from langchain_core.messages import SystemMessage, HumanMessage
from agents.state import AgentState
from agents.prompts import RESEARCH_CRITIQUE_PROMPT
from agents.utils import to_text


def research_critique_node(state: AgentState, model, tavily) -> dict:
    """Execute surgical searches to fill specific evidence gaps flagged during reflection.

    Args:
        state: Current agent state containing critique and draft.
        model: LLM for critique analysis and query formulation.
        tavily: TavilyClient for live search execution.

    Returns:
        State update containing new research content, tool call history, and reasoning traces.
    """
    critique_text = to_text(state.get('critique', ''))
    draft_text = to_text(state.get('draft', ''))
    task_text = to_text(state.get('task', ''))

    prompt = RESEARCH_CRITIQUE_PROMPT.format(
        draft=draft_text[:2000],
        critique=critique_text[:1500]
    )

    thought_process = "Formulating surgical queries to locate specific data and evidence requested by Reflection Agent."
    queries = [f"{task_text} specific data evidence", f"{task_text} detailed analysis"]

    try:
        response = model.invoke([
            SystemMessage(content="You are an autonomous research agent addressing critique gaps. Always return valid JSON."),
            HumanMessage(content=prompt)
        ])
        raw_text = to_text(response.content).strip()
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
        print(f"Research critique parse notice: {e}")
        queries = [f"{task_text} detailed metrics analysis"]

    content = list(state.get('content') or [])
    tool_calls_log = list(state.get('tool_calls_log') or [])
    new_tool_calls = []

    for q in queries:
        call_record = {
            "agent": "research_critique",
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
                    content.append(f"[Deepening: {title}] ({url}): {snippet}")
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
            "agent": "research_critique",
            "title": "Gap Remediation & Deep-Search",
            "summary": thought_process[:250] + ("..." if len(thought_process) > 250 else ""),
            "full_thought": thought_process,
            "queries_executed": queries,
            "tools_called": len(new_tool_calls)
        }
    }
