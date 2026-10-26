"""
Autonomous Multi-Agent Report System — Terminal Runner
======================================================
CLI runner for the multi-agent system. Demonstrates autonomous agent reasoning,
live tool executions, and quality-gate routing directly in the console.
"""

import os
import uuid
from dotenv import load_dotenv

load_dotenv()

from agents.graph_builder import build_graph


def run_cli():
    print("=" * 70)
    print(" 🚀 Autonomous Multi-Agent System (LangGraph + Gemini + Tavily)")
    print("=" * 70)

    task = input("\nEnter research topic (or press Enter for default):\n> ").strip()
    if not task:
        task = "Analyze the latest inflation figures and interest rate trajectory in the European Union."

    print(f"\n[System] Deploying multi-agent team on: '{task}'...\n")

    graph, memory = build_graph()
    thread = {"configurable": {"thread_id": str(uuid.uuid4())}}

    inputs = {
        "task": task,
        "max_revisions": 2,
        "revision_number": 1,
        "content": [],
        "tool_calls_log": [],
        "quality_score": 0,
        "pass_decision": False,
    }

    step_num = 1
    final_draft = ""

    for step in graph.stream(inputs, thread):
        for node_name, output in step.items():
            print(f"\n[{step_num}] AGENT ACTIVE: {node_name.upper()}")
            print("-" * 50)

            reasoning = output.get("agent_reasoning", {})
            if reasoning:
                thought = reasoning.get("full_thought") or reasoning.get("summary")
                if thought:
                    print(f"🧠 REASONING:\n{thought}\n")

            tools = [
                tc for tc in output.get("tool_calls_log", [])
                if tc.get("agent") == node_name
            ]
            if tools:
                print(f"🛠️  AUTONOMOUS TOOL CALLS ({len(tools)}):")
                for t in tools:
                    print(f"  • {t.get('tool')}: \"{t.get('query')}\" -> Status: {t.get('status')}")
                    for src in t.get("sources", []):
                        print(f"    🔗 {src.get('title')} ({src.get('url')})")
                print()

            if node_name == "reflect":
                score = output.get("quality_score", 0)
                decision = output.get("pass_decision", False)
                verdict = "PASSED (Quality Approved)" if decision else "REVISION REQUIRED (Gaps identified)"
                print(f"⚖️  QUALITY GATE: Score {score}/10 | Verdict: {verdict}")

            if "draft" in output:
                final_draft = output["draft"]
                rev = output.get("revision_number", 1) - 1
                print(f"✍️  Draft v{rev} generated ({len(final_draft.split())} words).")

            step_num += 1

    print("\n" + "=" * 70)
    print(" 🎉 WORKFLOW COMPLETED")
    print("=" * 70)
    print("\nFINAL REPORT:\n")
    print(final_draft)


if __name__ == "__main__":
    run_cli()
