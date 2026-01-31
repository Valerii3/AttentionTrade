"""
Gemini-based agent for propose flow: initial reasonability check (Google Search via generate_content + tools), tool selection, accept decision.
Uses GEMINI_API_KEY when set; otherwise falls back to event_definition + always accept.
"""
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_TOOL_IDS = ["hn_frontpage", "reddit"]


def initial_reasonability_check(
    name: str,
    source_url: Optional[str],
    description: Optional[str],
) -> dict[str, Any]:
    """
    Check if the event is reasonable using Gemini generate_content with Google Search tool.
    One call: model uses tools=[Tool(google_search=GoogleSearch())] to verify, returns pass/reason JSON.
    Returns {"pass": bool, "reason": str}. If not pass, reject the event with reason.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"pass": True, "reason": "No API key; skipping initial check."}

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except ImportError:
        return {"pass": True, "reason": "Gemini not available; skipping check."}

    user_parts = [f"Event name: {name}."]
    if source_url:
        user_parts.append(f"Source URL: {source_url}")
    if description:
        user_parts.append(f"Description: {description}")
    user_content = " ".join(user_parts)

    prompt = (
        "You check whether an event is suitable for an attention-trading market (tradable on attention). "
        "Use the event name and description (if provided) to understand what the event is. "
        "Use Google Search to verify the event is real and discussed on the web. "
        "If you find no or insufficient information, the event is not tradable. "
        "Reply with ONLY a JSON object: {\"pass\": true or false, \"reason\": \"short explanation\"}. "
        "If pass is false, reason should be user-friendly (e.g. \"We couldn't find enough information about this event on the web, so it's not tradable yet.\"). "
        "No markdown, no code fences.\n\n"
        + user_content
    )

    try:
        grounding_tool = genai.types.Tool(google_search=genai.types.GoogleSearch())
        config = genai.types.GenerateContentConfig(tools=[grounding_tool])
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=config,
        )
        # Log full Gemini response
        try:
            text = getattr(response, "text", None) or (
                response.candidates[0].content.parts[0].text
                if response.candidates and response.candidates[0].content.parts
                else None
            )
            if text:
                logger.info("Gemini reasonability response: %s", text[:2000] + ("..." if len(text) > 2000 else ""))
            else:
                logger.info("Gemini reasonability response: (no text)")
        except Exception as e:
            logger.warning("Could not log Gemini response: %s", e)

        if hasattr(response, "text") and response.text:
            text = (response.text or "").strip()
        elif response.candidates and response.candidates[0].content.parts:
            text = (response.candidates[0].content.parts[0].text or "").strip()
        else:
            logger.warning("No text in Gemini response; rejecting.")
            return {"pass": False, "reason": "No response from verification; event rejected."}

        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0].strip()
        out = json.loads(text)
        passed = bool(out.get("pass", False))
        reason = out.get("reason", "")
        logger.info("Reasonability: pass=%s, reason=%s", passed, reason)
        return {"pass": passed, "reason": reason}
    except json.JSONDecodeError as e:
        logger.warning("Gemini response not valid JSON: %s", e)
        return {"pass": False, "reason": "Verification response invalid; event rejected."}
    except Exception as exc:
        logger.warning("Error during initial check: %s", exc, exc_info=True)
        return {"pass": False, "reason": "Error during initial check; event rejected."}


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
            "channels": ["Hacker News", "Reddit", "GitHub", "LinkedIn"],
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
        "You are a config generator for an attention-tracking system. "
        "Use the event name and description (if provided) to decide which tools to use. "
        "Output ONLY a single JSON object with keys: tools (array of tool ids), keywords (array of strings), exclusions (array of strings). "
        "Available tools: Reddit (id: reddit), Hacker News (id: hn_frontpage), GitHub (id: github), LinkedIn (id: linkedin). "
        "Routing rules: "
        "If it's a meme or similar casual/viral content, use reddit. "
        "If it's technical (software, repos, dev tools), use hn_frontpage + reddit + github. "
        "If it's an event (conference, meetup, professional event), use linkedin. "
        "You can combine tools when the event fits multiple categories. No markdown, no explanation.\n\n"
        + user_content
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
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
        out["channels"] = ["Hacker News", "Reddit", "GitHub", "LinkedIn"]
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
            model="gemini-2.5-flash-lite",
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
