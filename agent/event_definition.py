"""
AI agent: given event name and time window, return channels, keywords, exclusions, and selected tools.
Uses LLM when OPENAI_API_KEY is set; otherwise returns a sensible default.
"""
import json
import os
from typing import Any, Optional

# Default tool ids when no LLM or fallback (must match backend tool registry)
DEFAULT_TOOL_IDS = ["hn_frontpage", "reddit"]


def event_definition(
    name: str,
    window_minutes: int,
    *,
    source_url: Optional[str] = None,
    description: Optional[str] = None,
    available_tools: Optional[list[dict[str, str]]] = None,
    suggest_window_only: bool = False,
) -> dict[str, Any]:
    """
    Return config with channels, keywords, exclusions, and tools.
    If suggest_window_only=True, window_minutes may be 0; response includes suggested_window_minutes.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    tools_list = available_tools or []
    if api_key:
        return _event_definition_llm(
            name, window_minutes, api_key,
            source_url=source_url,
            description=description,
            available_tools=tools_list,
            suggest_window_only=suggest_window_only,
        )
    return _event_definition_default(
        name, window_minutes,
        source_url=source_url,
        description=description,
        suggest_window_only=suggest_window_only,
    )


def _event_definition_default(
    name: str,
    window_minutes: int,
    *,
    source_url: Optional[str] = None,
    description: Optional[str] = None,
    suggest_window_only: bool = False,
) -> dict[str, Any]:
    """Default config when no LLM is configured."""
    name_lower = name.lower()
    words = [w for w in name_lower.replace("-", " ").split() if len(w) > 2][:5]
    keywords = list(set(words + [name_lower]))
    suggested = 60 if suggest_window_only else window_minutes
    return {
        "event": name,
        "channels": ["Hacker News", "Reddit"],
        "tools": DEFAULT_TOOL_IDS,
        "keywords": keywords[:10] if keywords else [name_lower],
        "exclusions": ["mouse cursor", "ui cursor", "cursor pointer"],
        "window_minutes": window_minutes if not suggest_window_only else 0,
        "suggested_window_minutes": suggested,
        "source_url": source_url,
        "description": description,
    }


def _event_definition_llm(
    name: str,
    window_minutes: int,
    api_key: str,
    *,
    source_url: Optional[str] = None,
    description: Optional[str] = None,
    available_tools: Optional[list[dict[str, str]]] = None,
    suggest_window_only: bool = False,
) -> dict[str, Any]:
    """Call OpenAI (or compatible) API for event definition and tool selection."""
    try:
        import httpx
        tools_list = available_tools or []
        tools_desc = json.dumps([{"id": t["id"], "name": t["name"], "description": t["description"]} for t in tools_list]) if tools_list else "[]"
        user_parts = [f"Event: {name}. Window: {window_minutes} minutes."]
        if source_url:
            user_parts.append(f"Source URL: {source_url}")
        if description:
            user_parts.append(f"Description: {description}")
        if suggest_window_only:
            user_parts.append("Suggest a reasonable window duration in minutes (suggested_window_minutes) only; do not fill other fetch-related fields beyond tools.")
        user_content = " ".join(user_parts)

        system_content = (
            "You are a config generator for an attention-tracking system. Given an event name and time window (and optional source URL or description), "
            "output ONLY a single JSON object with keys: event, tools (array of tool ids to use for this event), keywords (array of search terms), "
            "exclusions (array of terms to exclude), window_minutes (number). "
            "If suggested_window_minutes is requested, also include suggested_window_minutes (number). "
            "Available tools (id, name, description): " + tools_desc + ". "
            "Choose which tools are relevant (e.g. for a Reddit URL use reddit; for tech news use hn_frontpage). No markdown, no explanation."
        )
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.3,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0].strip()
        out = json.loads(content)
        out.setdefault("channels", ["Hacker News", "Reddit"])
        out.setdefault("tools", DEFAULT_TOOL_IDS)
        out.setdefault("keywords", [name])
        out.setdefault("exclusions", [])
        out["window_minutes"] = window_minutes if not suggest_window_only else out.get("window_minutes", 0)
        if suggest_window_only and "suggested_window_minutes" not in out:
            out["suggested_window_minutes"] = 60
        out["source_url"] = source_url
        out["description"] = description
        return out
    except Exception:
        return _event_definition_default(
            name, window_minutes,
            source_url=source_url,
            description=description,
            suggest_window_only=suggest_window_only,
        )
