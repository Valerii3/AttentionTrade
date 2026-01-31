"""
Gemini-based agent for propose flow: tool selection and accept decision.
Uses GEMINI_API_KEY when set; otherwise falls back to event_definition + always accept.
"""
import json
import os
from typing import Any, Optional

DEFAULT_TOOL_IDS = ["hn_frontpage", "reddit"]


def select_tools_and_config(
    name: str,
    source_url: Optional[str],
    description: Optional[str],
    available_tools: list[dict[str, str]],
    window_minutes: int,
) -> dict[str, Any]:
    """
    Return config with tools, keywords, exclusions for building the index.
    Uses Gemini when GEMINI_API_KEY is set; else falls back to event_definition.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _select_tools_fallback(name, source_url, description, window_minutes)
    return _select_tools_gemini(
        name, source_url, description, available_tools, window_minutes, api_key
    )


def _select_tools_fallback(
    name: str,
    source_url: Optional[str],
    description: Optional[str],
    window_minutes: int,
) -> dict[str, Any]:
    """Fallback when no Gemini key: use event_definition (OpenAI or default)."""
    try:
        from agent.event_definition import event_definition
        return event_definition(
            name,
            window_minutes,
            source_url=source_url,
            description=description,
            available_tools=None,
        )
    except Exception:
        name_lower = name.lower()
        words = [w for w in name_lower.replace("-", " ").split() if len(w) > 2][:5]
        keywords = list(set(words + [name_lower]))
        return {
            "event": name,
            "channels": ["Hacker News", "Reddit"],
            "tools": DEFAULT_TOOL_IDS,
            "keywords": keywords[:10] if keywords else [name_lower],
            "exclusions": ["mouse cursor", "ui cursor", "cursor pointer"],
            "window_minutes": window_minutes,
            "source_url": source_url,
            "description": description,
        }


def _select_tools_gemini(
    name: str,
    source_url: Optional[str],
    description: Optional[str],
    available_tools: list[dict[str, str]],
    window_minutes: int,
    api_key: str,
) -> dict[str, Any]:
    """Call Gemini to choose tools and keywords."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except ImportError:
        return _select_tools_fallback(name, source_url, description, window_minutes)

    tools_desc = json.dumps([{"id": t["id"], "name": t.get("name", ""), "description": t.get("description", "")} for t in available_tools]) if available_tools else "[]"
    user_parts = [f"Event name: {name}. Window: {window_minutes} minutes."]
    if source_url:
        user_parts.append(f"Source URL: {source_url}")
    if description:
        user_parts.append(f"Description: {description}")
    user_content = " ".join(user_parts)

    full_prompt = (
        "You are a config generator for an attention-tracking system. Given an event name and optional URL/description, "
        "output ONLY a single JSON object with keys: tools (array of tool ids to use), keywords (array of search terms), exclusions (array of terms to exclude). "
        "Available tools: " + tools_desc + ". "
        "Choose which tools are relevant (e.g. for a Reddit URL use reddit; for tech news use hn_frontpage). No markdown, no explanation.\n\n"
        + user_content
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_prompt,
        )
        # Handle both config and no config; some SDK versions use different signatures
        if hasattr(response, "text"):
            text = response.text
        elif response.candidates and response.candidates[0].content.parts:
            text = response.candidates[0].content.parts[0].text
        else:
            return _select_tools_fallback(name, source_url, description, window_minutes)

        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0].strip()
        out = json.loads(text)
        out.setdefault("tools", DEFAULT_TOOL_IDS)
        out.setdefault("keywords", [name])
        out.setdefault("exclusions", [])
        out["event"] = name
        out["channels"] = ["Hacker News", "Reddit"]
        out["window_minutes"] = window_minutes
        out["source_url"] = source_url
        out["description"] = description
        return out
    except Exception:
        return _select_tools_fallback(name, source_url, description, window_minutes)


def should_accept_event(
    name: str,
    index_value: float,
    activity: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """
    Return whether the event is acceptable to trade on (e.g. based on traction).
    Uses Gemini when GEMINI_API_KEY is set; else always accept for demo.
    Returns dict with accept: bool, reason?: str.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"accept": True, "reason": "Demo mode: accepted by default."}

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except ImportError:
        return {"accept": True, "reason": "Gemini not available; accepted by default."}

    activity_str = json.dumps(activity) if activity else "{}"
    prompt = (
        f"Event: {name}. Initial index (traction): {index_value}. Per-channel activity: {activity_str}. "
        "Should we accept this event for trading (is there enough traction)? "
        "Reply with ONLY a JSON object: {\"accept\": true or false, \"reason\": \"short reason\"}. No markdown."
    )
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        if hasattr(response, "text"):
            text = response.text
        elif response.candidates and response.candidates[0].content.parts:
            text = response.candidates[0].content.parts[0].text
        else:
            return {"accept": True, "reason": "Could not parse response; accepted by default."}

        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0].strip()
        out = json.loads(text)
        return {"accept": bool(out.get("accept", True)), "reason": out.get("reason", "")}
    except Exception:
        return {"accept": True, "reason": "Error calling Gemini; accepted by default."}
