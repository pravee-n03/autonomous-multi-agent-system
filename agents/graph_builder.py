"""
Graph Builder
==============
Constructs and compiles the LangGraph multi-agent workflow.
Implements dynamic quality-gate routing where the Reflection Agent's
quality score and pass decision autonomously determine whether to
finalize the report or route to gap-remediation research.
Supports real-time node execution lifecycle hooks.
"""

import os
from functools import partial
from dotenv import load_dotenv

load_dotenv()

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import TavilyClient

from agents.state import AgentState
from agents.planner import plan_node
from agents.researcher import research_plan_node
from agents.generator import generation_node
from agents.reflector import reflection_node
from agents.research_critic import research_critique_node


def evaluate_quality_gate(state: AgentState):
    """Quality Gate routing function.

    The Reflection Agent's autonomous decision determines the flow:
    - If the Reflection Agent grants a PASS (pass_decision=True or quality_score >= 8)
      after revision pass (curr_rev > 2), the workflow completes successfully (END).
    - If the draft needs revision, check if safety limit (max_revisions) was reached.
      If max revisions reached -> END.
      Otherwise -> route to 'research_critique' to gather surgical evidence for the gaps.
    """
    pass_decision = state.get("pass_decision", False)
    quality_score = state.get("quality_score", 0)
    curr_rev = state.get("revision_number", 1)
    max_rev = state.get("max_revisions", 2)

    print(f"🚦 Quality Gate Evaluation: Score={quality_score}/10, Pass={pass_decision}, Revision={curr_rev}/{max_rev}")

    # If revised (curr_rev > 2) and approved by reflection agent, complete workflow
    if (pass_decision or quality_score >= 8) and curr_rev > 2:
        print("✅ Reflection Agent APPROVED the revised report. Workflow complete.")
        return END

    # Safety ceiling: avoid infinite loops if revisions exceed limit
    # Note: curr_rev is incremented in generation_node (rev 1 produces draft 1 with rev=2; rev 2 produces draft 2 with rev=3)
    if curr_rev > max_rev + 1:
        print("⚠️ Max revisions safety threshold reached. Completing workflow.")
        return END

    # Otherwise, agent flagged deficiencies: route to targeted research critique
    print("🔄 Reflection Agent flagged gaps. Routing to research_critique (Fact-Checker).")
    return "research_critique"


def wrap_node_with_hook(node_name: str, node_func, on_node_start=None):
    """Wrap a node function to invoke on_node_start hook right before execution."""
    def wrapper(state: AgentState):
        if on_node_start:
            try:
                on_node_start(node_name, state)
            except Exception as e:
                print(f"Hook notice for {node_name}: {e}")
        return node_func(state)
    return wrapper


def build_graph(on_node_start=None):
    """Build and return the compiled LangGraph workflow.

    Args:
        on_node_start: Optional callback function(node_name, state) called immediately
                       when any agent node begins execution.

    Returns:
        Tuple of (compiled_graph, memory_saver)
    """
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    tavily_api_key = os.environ.get("TAVILY_API_KEY")

    model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=google_api_key
    )
    tavily = TavilyClient(api_key=tavily_api_key)

    bound_plan = partial(plan_node, model=model)
    bound_research_plan = partial(research_plan_node, model=model, tavily=tavily)
    bound_generate = partial(generation_node, model=model)
    bound_reflect = partial(reflection_node, model=model)
    bound_research_critique = partial(research_critique_node, model=model, tavily=tavily)

    builder = StateGraph(AgentState)

    # Add agent nodes with execution start hooks
    builder.add_node("planner", wrap_node_with_hook("planner", bound_plan, on_node_start))
    builder.add_node("research_plan", wrap_node_with_hook("research_plan", bound_research_plan, on_node_start))
    builder.add_node("generate", wrap_node_with_hook("generate", bound_generate, on_node_start))
    builder.add_node("reflect", wrap_node_with_hook("reflect", bound_reflect, on_node_start))
    builder.add_node("research_critique", wrap_node_with_hook("research_critique", bound_research_critique, on_node_start))

    # Set entry point
    builder.set_entry_point("planner")

    # Workflow topology:
    # 1. Planner designs the blueprint
    builder.add_edge("planner", "research_plan")
    # 2. Researcher finds initial facts
    builder.add_edge("research_plan", "generate")
    # 3. Generator writes the draft
    builder.add_edge("generate", "reflect")
    # 4. Reflection Agent inspects the draft and autonomously decides:
    #    -> PASS (END) or FAIL (route to research_critique)
    builder.add_conditional_edges(
        "reflect",
        evaluate_quality_gate,
        {
            END: END,
            "research_critique": "research_critique"
        }
    )
    # 5. Research Critique investigates specific gaps and feeds back into generator
    builder.add_edge("research_critique", "generate")

    memory = InMemorySaver()
    graph = builder.compile(checkpointer=memory)

    return graph, memory
