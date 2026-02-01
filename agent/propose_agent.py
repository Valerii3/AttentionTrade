"""
Gemini-based agent for propose flow: initial reasonability check (Google Search via generate_content + tools), tool selection, accept decision.
Uses GEMINI_API_KEY when set; otherwise falls back to event_definition + always accept.
"""
import json
import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_TOOL_IDS = ["hn_frontpage", "reddit"]


def _parse_first_json(text: str) -> Optional[dict[str, Any]]:
    """Parse the first JSON object from text. Handles Gemini returning extra content after the JSON (e.g. line 2)."""
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        if "Extra data" not in str(e):
            raise
    # Extra data: take only the first JSON object (find matching brace)
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None

# Minimum total activity (sum over channels) to consider event tradable
MIN_TRACTION_SCORE = 0.5

NO_ATTENTION_REASON = (
    "There isn't enough attention for this event yet, so it's not tradable."
)

OUTCOME_STYLE_SUGGESTION = (
    "This is an outcome market (resolvable by checking one number). "
    "Try instead: \"Will attention around [your topic] increase in the next 60 minutes?\""
)


def has_traction(activity: Optional[dict[str, float]]) -> bool:
    """Return True if total activity meets the traction threshold (event is tradable)."""
    if not activity:
        return False
    total = sum(activity.values())
    return total >= MIN_TRACTION_SCORE


def reject_reason_if_outcome_style(name: str, description: Optional[str]) -> Optional[str]:
    """
    If the event name/description looks like an outcome-style market (resolvable by one number), return a reject reason.
    Otherwise return None. Used to enforce attention-native framing.
    """
    text = f"{name} {description or ''}".lower()
    # N stars/likes/followers/users/downloads
    if re.search(r"\d+\s*(stars?|likes?|followers?|users?|downloads?|subscribers?)", text):
        return OUTCOME_STYLE_SUGGESTION
    # by Friday / by tomorrow / before date
    if re.search(r"\b(by|before)\s+(friday|monday|tuesday|wednesday|thursday|saturday|sunday|tomorrow|next\s+week|\d)", text):
        return OUTCOME_STYLE_SUGGESTION
    # get/hit/reach N (number)
    if re.search(r"\b(get|hit|reach)\s+\d+", text):
        return OUTCOME_STYLE_SUGGESTION
    # "100 GitHub stars" style
    if re.search(r"\d+\s*(github\s+)?stars?", text) or re.search(r"stars?\s*by\s", text):
        return OUTCOME_STYLE_SUGGESTION
    # "will X launch" (product launch = one fact)
    if re.search(r"\bwill\s+.+\s+launch\b", text):
        return OUTCOME_STYLE_SUGGESTION
    return None


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
        return {"pass": True, "reason": "No API key; skipping initial check.", "should_build_index": True}

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except ImportError:
        return {"pass": True, "reason": "Gemini not available; skipping check.", "should_build_index": True}

    user_parts = [f"Event name: {name}."]
    if source_url:
        user_parts.append(f"Source URL: {source_url}")
    if description:
        user_parts.append(f"Description: {description}")
    user_content = " ".join(user_parts)

    prompt = (
        "You check whether an event is suitable for an attention-trading market (tradable on attention). "
        "Rules: (1) The event must be about ATTENTION (e.g. 'Will attention around X increase?'), not an outcome resolvable by one number. "
        "If the event is an outcome market (e.g. 'Will X get 100 stars by Friday?', 'Will X hit N users?', 'Will X launch?'), reply with pass: false and reason: \"This is an outcome market (resolvable by checking one number). Try instead: Will attention around [topic] increase in the next 60 minutes?\" "
        "(2) Use the event name and description to understand what the event is. (3) Use Google Search to verify the event is real. "
        "Be permissive: if the topic is real and has any discussion (including YouTube, social, news), pass is true. Only reject for spam or clearly fake topics. "
        "(4) should_build_index: set true whenever we can build an index (we have YouTube for non-tech and HN/Reddit for tech). Default to true so we try to build; set false only for completely obscure or unverifiable topics. "
        "Reply with ONLY a JSON object: {\"pass\": true or false, \"reason\": \"short explanation\", \"should_build_index\": true or false}. "
        "If pass is false, reason should be user-friendly. No markdown, no code fences.\n\n"
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
        # Extract text: try .text first, then candidates[0].content.parts (some parts may be tool_call, not text)
        text = None
        try:
            if getattr(response, "text", None):
                text = (response.text or "").strip()
            if not text and getattr(response, "candidates", None) and len(response.candidates) > 0:
                c = response.candidates[0]
                content = getattr(c, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if parts:
                    text_parts = [
                        part.text for part in parts
                        if getattr(part, "text", None) and (part.text or "").strip()
                    ]
                    if text_parts:
                        text = " ".join(text_parts).strip()
        except Exception as e:
            logger.warning("Could not extract Gemini response text: %s", e)

        if not text:
            # Log why we got no text (safety block, empty candidates, etc.)
            block_reason = None
            try:
                if getattr(response, "prompt_feedback", None):
                    pf = response.prompt_feedback
                    block_reason = getattr(pf, "block_reason", None) or getattr(pf, "block_reason_name", None)
                if block_reason is None and getattr(response, "candidates", None) and len(response.candidates) > 0:
                    c = response.candidates[0]
                    block_reason = getattr(c, "finish_reason", None) or getattr(c, "finish_reason_name", None)
            except Exception as e:
                logger.warning("Could not get block reason: %s", e)
            reason_msg = "No response from verification; event rejected."
            if block_reason is not None:
                reason_msg = f"Verification blocked ({block_reason}); try rephrasing or a different topic."
                logger.warning("No text in Gemini response; block_reason=%s", block_reason)
            else:
                logger.warning("No text in Gemini response; rejecting.")
            return {"pass": False, "reason": reason_msg, "should_build_index": False}

        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0].strip()
        out = _parse_first_json(text)
        if out is None:
            logger.warning("Gemini response not valid JSON (could not extract object)")
            return {"pass": False, "reason": "Verification response invalid; event rejected.", "should_build_index": False}
        passed = bool(out.get("pass", False))
        reason = out.get("reason", "")
        should_build_index = bool(out.get("should_build_index", True))
        logger.info("Reasonability: pass=%s, reason=%s, should_build_index=%s", passed, reason, should_build_index)
        return {"pass": passed, "reason": reason, "should_build_index": should_build_index}
    except json.JSONDecodeError as e:
        logger.warning("Gemini response not valid JSON: %s", e)
        return {"pass": False, "reason": "Verification response invalid; event rejected.", "should_build_index": False}
    except Exception as exc:
        logger.warning("Error during initial check: %s", exc, exc_info=True)
        return {"pass": False, "reason": "Error during initial check; event rejected.", "should_build_index": False}


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
            "channels": ["Hacker News", "Reddit", "YouTube", "GitHub", "LinkedIn"],
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
        "Available tools: Hacker News (id: hn_frontpage), Reddit (id: reddit), YouTube (id: youtube), GitHub (id: github), LinkedIn (id: linkedin). "
        "Routing rules: "
        "If it's NOT technical (entertainment, general, viral, music, sports, culture), use youtube (and optionally reddit). "
        "If it's technical (software, repos, dev tools), use hn_frontpage + reddit + github. "
        "If it's a meme or casual/viral, use reddit + youtube. "
        "If it's an event (conference, meetup, professional), use linkedin. "
        "You can combine tools. No markdown, no explanation.\n\n"
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
        out = _parse_first_json(text)
        if out is None:
            return _select_tools_fallback(name, source_url, description, window_minutes)
        out.setdefault("tools", DEFAULT_TOOL_IDS)
        out.setdefault("keywords", [name])
        out.setdefault("exclusions", [])
        out["event"] = name
        out["channels"] = ["Hacker News", "Reddit", "YouTube", "GitHub", "LinkedIn"]
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
        out = _parse_first_json(text)
        if out is None:
            return {"accept": True, "reason": "Could not parse response; accepted by default."}
        return {"accept": bool(out.get("accept", True)), "reason": out.get("reason", "")}
    except Exception:
        return {"accept": True, "reason": "Error calling Gemini; accepted by default."}


def suggest_headline_subline(
    name: str,
    market_type: str,
    *,
    source_url: Optional[str] = None,
    description: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return headline (emotional hook) and subline (precise) for the market card/detail.
    Optional label_up / label_down for buttons (e.g. "Heating up" / "Cooling down").
    Uses Gemini when GEMINI_API_KEY set; else sensible defaults.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _headline_subline_default(name, market_type)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except ImportError:
        return _headline_subline_default(name, market_type)

    window_desc = "next 60 min" if market_type == "1h" else "next 24h"
    subline_template = "Attention change · next 60 min" if market_type == "1h" else "Sustained attention · next 24h"
    user_parts = [f"Topic/event name: {name}. Window: {window_desc}."]
    if source_url:
        user_parts.append(f"Source URL: {source_url}")
    if description:
        user_parts.append(f"Description: {description}")
    user_content = " ".join(user_parts)

    prompt = (
        "You write a short, punchy HEADLINE and SUBLINE for an attention market card. "
        "Rules: HEADLINE = emotional hook, human language (e.g. 'Is Clawdbot gaining momentum?', 'Is the Cursor Hackathon heating up?', 'Is the Attention Economy narrative accelerating?'). "
        "SUBLINE = precise, same for all: either 'Attention change · next 60 min' or 'Sustained attention · next 24h' depending on window. "
        "Also output two short button labels: label_up (for betting attention goes up, e.g. 'Heating up' or 'Momentum ↑') and label_down (e.g. 'Cooling down' or 'Momentum ↓'). "
        "Reply with ONLY a JSON object: {\"headline\": \"...\", \"subline\": \"...\", \"label_up\": \"...\", \"label_down\": \"...\"}. No markdown."
        + "\n\n" + user_content
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
            return _headline_subline_default(name, market_type)
        text = (text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0].strip()
        out = _parse_first_json(text)
        if out is None:
            return _headline_subline_default(name, market_type)
        headline = (out.get("headline") or "").strip() or _headline_subline_default(name, market_type)["headline"]
        subline = (out.get("subline") or "").strip() or ("Attention change · next 60 min" if market_type == "1h" else "Sustained attention · next 24h")
        label_up = (out.get("label_up") or "").strip() or "Heating up"
        label_down = (out.get("label_down") or "").strip() or "Cooling down"
        return {"headline": headline, "subline": subline, "label_up": label_up, "label_down": label_down}
    except Exception:
        return _headline_subline_default(name, market_type)


def _headline_subline_default(name: str, market_type: str) -> dict[str, Any]:
    """Default headline/subline when no Gemini."""
    if market_type == "24h":
        headline = f"Will {name} stay hot?"
        subline = "Sustained attention · next 24h"
    else:
        headline = f"Is {name} gaining momentum?"
        subline = "Attention change · next 60 min"
    return {
        "headline": headline,
        "subline": subline,
        "label_up": "Heating up",
        "label_down": "Cooling down",
    }


def generate_event_image(
    name: str,
    headline: str,
    event_id: str,
    output_dir: str,
) -> Optional[str]:
    """
    Generate a square thumbnail image for the event using Gemini image generation.
    Saves to output_dir/{event_id}.png. Returns the file path on success, None on failure.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except ImportError:
        return None

    prompt = (
        f"Create a small square thumbnail image for a prediction market event card. "
        f"Theme: {name}. Headline/topic: {headline}. "
        "Style: iconic, clean, suitable for a card thumbnail (square crop). "
        "Muted colors with one accent. No text or words in the image. "
        "Simple, recognizable scene or symbol that represents the topic."
    )
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
        )
        parts = getattr(response, "parts", None) or (
            response.candidates[0].content.parts
            if response.candidates and response.candidates[0].content.parts
            else []
        )
        for part in parts:
            if getattr(part, "inline_data", None) is not None:
                img = getattr(part, "as_image", lambda: None)()
                if img is not None and callable(getattr(img, "save", None)):
                    os.makedirs(output_dir, exist_ok=True)
                    path = os.path.join(output_dir, f"{event_id}.png")
                    img.save(path)
                    return path
        return None
    except Exception as e:
        logger.warning("Gemini image generation failed: %s", e)
        return None
