"""
Multi-Agent Report Writer — FastAPI Application
=================================================
Serves the visual frontend and provides a WebSocket endpoint
that streams real-time agent activity, reasoning traces, tool executions,
and quality evaluations as the LangGraph workflow executes.

Run:
    python app.py
"""

import os
import json
import asyncio
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from agents.graph_builder import build_graph
from agents.utils import to_text


# ── Agent metadata for the frontend ──────────────────────────────────────

AGENT_META = {
    "planner": {
        "name": "Planning Agent",
        "icon": "📋",
        "color": "#09090b",
        "role": "Architect",
        "description": "Formulates strategic outline, research targets, and report blueprint",
    },
    "research_plan": {
        "name": "Research Agent",
        "icon": "🔍",
        "color": "#09090b",
        "role": "Investigator",
        "description": "Autonomously searches live web, parses sources, and gathers statistical data",
    },
    "generate": {
        "name": "Generation Agent",
        "icon": "✍️",
        "color": "#09090b",
        "role": "Synthesizer",
        "description": "Synthesizes multi-source research into an authoritative structured report",
    },
    "reflect": {
        "name": "Reflection Agent",
        "icon": "⚖️",
        "color": "#09090b",
        "role": "Quality Auditor",
        "description": "Audits draft against standards, assigns 1-10 quality score, and decides PASS/REVISION",
    },
    "research_critique": {
        "name": "Research Critique Agent",
        "icon": "🧪",
        "color": "#09090b",
        "role": "Fact-Checker",
        "description": "Performs surgical web searches to remediate specific factual gaps identified by Reflection",
    },
}


app = FastAPI(title="Multi-Agent Report Writer")

# Serve static files (frontend)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Routes ────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    """Serve the main frontend page."""
    return FileResponse(str(static_dir / "index.html"))


@app.get("/api/agents")
async def get_agents():
    """Return agent metadata and quality gate topology for frontend rendering."""
    workflow = [
        {"id": "planner", **AGENT_META["planner"]},
        {"id": "research_plan", **AGENT_META["research_plan"]},
        {"id": "generate", **AGENT_META["generate"]},
        {"id": "reflect", **AGENT_META["reflect"]},
        {"id": "research_critique", **AGENT_META["research_critique"]},
    ]
    edges = [
        {"from": "planner", "to": "research_plan"},
        {"from": "research_plan", "to": "generate"},
        {"from": "generate", "to": "reflect"},
        {"from": "reflect", "to": "research_critique", "label": "Needs Revision"},
        {"from": "reflect", "to": "__end__", "label": "Quality Pass (Score ≥ 8)"},
        {"from": "research_critique", "to": "generate", "label": "Enriched Evidence"},
    ]
    return {"agents": workflow, "edges": edges}


@app.websocket("/ws/run")
async def run_workflow(ws: WebSocket):
    """WebSocket endpoint that streams genuine multi-agent execution.

    Streams:
    - Real-time agent start signals ('agent_start')
    - Agent reasoning traces (Thought process)
    - Autonomous Tool calls & web search sources
    - Draft updates & revision versions
    - Quality score gauge (1-10) and pass/fail gate decisions
    """
    await ws.accept()

    try:
        data = await ws.receive_text()
        payload = json.loads(data)
        task = payload.get("task", "Analyze European Union inflation figures and ECB interest rate policy forecasts.")
        max_revisions = int(payload.get("max_revisions", 2))

        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        def on_node_start_hook(node_name: str, state: dict):
            """Invoked immediately when an agent node begins running."""
            loop.call_soon_threadsafe(queue.put_nowait, ("node_start", {
                "node_name": node_name,
                "revision_number": state.get("revision_number", 1)
            }))

        # Compile a dedicated graph instance with start hook for this session
        graph, memory = build_graph(on_node_start=on_node_start_hook)
        thread_id = str(uuid.uuid4())
        thread = {"configurable": {"thread_id": thread_id}}

        # Notify frontend workflow has started
        await ws.send_text(json.dumps({
            "type": "workflow_start",
            "task": task,
            "max_revisions": max_revisions,
        }))

        def run_graph_sync():
            try:
                for step_output in graph.stream(
                    {
                        "task": task,
                        "max_revisions": max_revisions,
                        "revision_number": 1,
                        "content": [],
                        "tool_calls_log": [],
                        "quality_score": 0,
                        "pass_decision": False,
                    },
                    thread,
                ):
                    loop.call_soon_threadsafe(queue.put_nowait, ("step", step_output))
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
            except Exception as exc:
                import traceback
                traceback.print_exc()
                loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))

        # Run streaming in background executor
        loop.run_in_executor(None, run_graph_sync)

        while True:
            msg_type, data_item = await queue.get()

            if msg_type == "error":
                await ws.send_text(json.dumps({
                    "type": "error",
                    "message": str(data_item),
                }))
                break

            elif msg_type == "done":
                await ws.send_text(json.dumps({"type": "workflow_complete"}))
                break

            elif msg_type == "node_start":
                node_name = data_item["node_name"]
                meta = AGENT_META.get(node_name, {
                    "name": node_name,
                    "icon": "🤖",
                    "role": "Agent",
                    "description": "",
                })
                await ws.send_text(json.dumps({
                    "type": "agent_start",
                    "agent_id": node_name,
                    "agent_name": meta["name"],
                    "agent_icon": meta["icon"],
                    "agent_role": meta.get("role", "Agent"),
                    "agent_description": meta["description"],
                    "revision_number": data_item.get("revision_number", 1)
                }))

            elif msg_type == "step":
                for node_name, node_output in data_item.items():
                    meta = AGENT_META.get(node_name, {
                        "name": node_name,
                        "icon": "🤖",
                        "color": "#09090b",
                        "role": "Agent",
                        "description": "",
                    })

                    event = {
                        "type": "agent_step",
                        "agent_id": node_name,
                        "agent_name": meta["name"],
                        "agent_icon": meta["icon"],
                        "agent_color": meta["color"],
                        "agent_role": meta.get("role", "Agent"),
                        "agent_description": meta["description"],
                        "reasoning": node_output.get("agent_reasoning", {}),
                        "quality_score": node_output.get("quality_score"),
                        "pass_decision": node_output.get("pass_decision"),
                        "tool_calls": [
                            tc for tc in node_output.get("tool_calls_log", [])
                            if tc.get("agent") == node_name
                        ],
                    }

                    if node_name == "planner":
                        event["output"] = to_text(node_output.get("plan", ""))
                    elif node_name == "research_plan":
                        event["output"] = f"Autonomously executed search queries and analyzed results."
                        event["detail"] = f"Gathered {len(node_output.get('content', []))} verified data snippets"
                    elif node_name == "generate":
                        event["output"] = to_text(node_output.get("draft", ""))
                        event["revision_number"] = node_output.get("revision_number", 1) - 1
                    elif node_name == "reflect":
                        event["output"] = to_text(node_output.get("critique", ""))
                    elif node_name == "research_critique":
                        event["output"] = "Executed surgical gap remediation web searches."
                        event["detail"] = f"Total research corpus: {len(node_output.get('content', []))} snippets"

                    await ws.send_text(json.dumps(event))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(json.dumps({
                "type": "error",
                "message": str(e),
            }))
        except Exception:
            pass


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  🚀 Multi-Agent System Ready!")
    print("  Open your browser at: http://127.0.0.1:8000")
    print("=" * 60 + "\n")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
