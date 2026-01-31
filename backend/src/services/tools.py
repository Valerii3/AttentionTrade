"""
Tool registry: data sources the agent can select for building an event index.
Each tool has id, name, and description (for LLM selection). Fetchers live in index_pipeline.
"""
from typing import TypedDict


class Tool(TypedDict):
    id: str
    name: str
    description: str


# Registry: id must match mapping in index_pipeline (TOOL_ID_TO_FETCHER)
TOOLS: list[Tool] = [
    {
        "id": "hn_frontpage",
        "name": "Hacker News",
        "description": "Fetches Hacker News front page RSS; counts items matching keywords.",
    },
    {
        "id": "reddit",
        "name": "Reddit",
        "description": "Fetches Reddit subreddit or post (placeholder; real impl would use Reddit API).",
    },
]


def get_available_tools() -> list[Tool]:
    """Return the list of tools for the agent to choose from."""
    return list(TOOLS)


def get_tool_ids() -> list[str]:
    """Return list of valid tool ids."""
    return [t["id"] for t in TOOLS]
