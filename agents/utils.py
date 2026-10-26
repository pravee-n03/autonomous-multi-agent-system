"""
Utility functions for multi-agent system.
"""

def to_text(content) -> str:
    """Normalize LLM response content into a plain string.

    ChatGoogleGenerativeAI may return content either as a plain string
    or as a list of dicts/parts like [{'type': 'text', 'text': '...'}].
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            elif hasattr(item, "text"):
                parts.append(str(item.text))
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content) if content is not None else ""
