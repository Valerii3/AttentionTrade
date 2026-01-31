"""
AI agent: given event name and time window, return channels, keywords, exclusions.
Uses LLM when OPENAI_API_KEY is set; otherwise returns a sensible default.
"""
import json
import os
from typing import Any


def event_definition(name: str, window_minutes: int) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return _event_definition_llm(name, window_minutes, api_key)
    return _event_definition_default(name, window_minutes)


def _event_definition_default(name: str, window_minutes: int) -> dict[str, Any]:
    """Default config when no LLM is configured."""
    name_lower = name.lower()
    # Simple keyword extraction: use first few words + common tech terms
    words = [w for w in name_lower.replace("-", " ").split() if len(w) > 2][:5]
    keywords = list(set(words + [name_lower]))
    return {
        "event": name,
        "channels": ["Hacker News", "Reddit"],
        "keywords": keywords[:10] if keywords else [name_lower],
        "exclusions": ["mouse cursor", "ui cursor", "cursor pointer"],
        "window_minutes": window_minutes,
    }


def _event_definition_llm(name: str, window_minutes: int, api_key: str) -> dict[str, Any]:
    """Call OpenAI (or compatible) API for event definition."""
    try:
        import httpx
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a config generator for an attention-tracking system. Given an event name and time window, output ONLY a single JSON object with keys: event, channels (array of strings, e.g. Hacker News, Reddit, GitHub), keywords (array of search terms), exclusions (array of terms to exclude), window_minutes (number). No markdown, no explanation."
                    },
                    {
                        "role": "user",
                        "content": f"Event: {name}. Window: {window_minutes} minutes."
                    }
                ],
                "temperature": 0.3,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        # Strip markdown code block if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0].strip()
        out = json.loads(content)
        out.setdefault("channels", ["Hacker News", "Reddit"])
        out.setdefault("keywords", [name])
        out.setdefault("exclusions", [])
        out["window_minutes"] = window_minutes
        return out
    except Exception:
        return _event_definition_default(name, window_minutes)
