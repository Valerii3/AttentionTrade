"""
Tool registry: data sources the agent can select for building an event index.
Each tool has id, name, and description (for LLM selection). Fetchers live in index_pipeline.
"""
from typing import TypedDict


class Tool(TypedDict):
    id: str
    name: str
    description: str


# Registry: id must match mapping in index_pipeline (_get_tool_fetchers)
TOOLS: list[Tool] = [
    {
        "id": "hn_frontpage",
        "name": "Hacker News",
        "description": "Hacker News search (Algolia) over the event window; stories matching keywords, scored by count and engagement (points).",
    },
    {
        "id": "reddit",
        "name": "Reddit",
        "description": "Fetches Reddit subreddit or post (placeholder; real impl would use Reddit API).",
    },
    {
        "id": "youtube",
        "name": "YouTube",
        "description": "YouTube videos (search last 30 days); engagement from views, likes, comments. Use for non-tech / general / entertainment.",
    },
    {
        "id": "github",
        "name": "GitHub",
        "description": "Fetches GitHub repos/activity (placeholder; real impl TBD).",
    },
    {
        "id": "linkedin",
        "name": "LinkedIn",
        "description": "Fetches LinkedIn events/posts (placeholder; real impl TBD).",
    },
]


def get_available_tools() -> list[Tool]:
    """Return the list of tools for the agent to choose from."""
    return list(TOOLS)


def get_tool_ids() -> list[str]:
    """Return list of valid tool ids."""
    return [t["id"] for t in TOOLS]
