"""
Agent Tools
============
Tools that agents can autonomously decide to call.
These are LangChain tools bound to agents via bind_tools(),
so the LLM itself decides when and what to search — not hardcoded logic.
"""

from langchain_core.tools import tool


def create_search_tool(tavily_client):
    """Factory that creates a web_search tool backed by a Tavily client.

    The returned tool is passed to model.bind_tools() so the LLM
    can autonomously decide when to call it.
    """

    @tool
    def web_search(query: str) -> str:
        """Search the web for current information, data, statistics, and facts.
        Use this tool when you need to find specific information about a topic.
        You can call this multiple times with different queries to build
        comprehensive research. Each call should target a different aspect."""
        try:
            response = tavily_client.search(query=query, max_results=3)
            results = []
            for r in response.get("results", []):
                source = r.get("url", "Unknown source")
                content = r.get("content", "")
                results.append(f"[Source: {source}]\n{content}")
            return (
                "\n\n---\n\n".join(results)
                if results
                else "No relevant results found for this query."
            )
        except Exception as e:
            return f"Search encountered an issue: {str(e)}. Try a different query."

    return web_search
