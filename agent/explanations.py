"""
AI agent: given event and index snapshots, produce a short explanation of what drove the index.
Also: live market context (Gemini + Google Search) for why attention is fading / flat / rising.
"""
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def explain_index_movement(
    event_name: str,
    index_start: float,
    index_end: float,
    snapshots: list[dict[str, Any]],
) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return _explain_llm(event_name, index_start, index_end, snapshots, api_key)
    return _explain_default(index_start, index_end)


def _explain_default(index_start: float, index_end: float) -> str:
    if index_end > index_start:
        return "Attention increased over the window (index rose)."
    if index_end < index_start:
        return "Attention decreased over the window (index fell)."
    return "Attention stayed roughly flat over the window."


def _explain_llm(
    event_name: str,
    index_start: float,
    index_end: float,
    snapshots: list[dict[str, Any]],
    api_key: str,
) -> str:
    try:
        import httpx
        summary = json.dumps(snapshots[-10:] if len(snapshots) > 10 else snapshots)
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You summarize why an attention index moved in one or two short sentences. Be factual and refer to the index values. No markdown."
                    },
                    {
                        "role": "user",
                        "content": f"Event: {event_name}. Index started at {index_start}, ended at {index_end}. Recent snapshots: {summary}. Why did attention move?"
                    }
                ],
                "temperature": 0.3,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        return content or _explain_default(index_start, index_end)
    except Exception:
        return _explain_default(index_start, index_end)


def market_context(
    event_name: str,
    index_start: float,
    index_current: float,
    snapshots: list[dict[str, Any]],
) -> Optional[str]:
    """
    Use Gemini with Google Search to explain what's going on with this topic
    and why attention is fading / staying flat / rising (2–4 sentences).
    Returns None if Gemini/API is unavailable or fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except ImportError:
        return None

    recent = snapshots[-15:] if len(snapshots) > 15 else snapshots
    summary = json.dumps(recent)
    direction = "rising" if index_current > index_start else ("falling" if index_current < index_start else "flat")

    prompt = (
        "You are explaining an attention market: how much buzz there is around a topic over time. "
        "Use Google Search once to find recent news or discussion about this topic. "
        "Then in 2–4 short sentences, explain what's going on with this topic in the world "
        "and why attention is " + direction + " (or staying flat). "
        "Be factual and concise. No markdown, no bullet points.\n\n"
        f"Event/topic: {event_name}. "
        f"Attention index: started at {index_start:.1f}, now {index_current:.1f} (trend: {direction}). "
        f"Recent index snapshots: {summary}."
    )

    try:
        grounding_tool = genai.types.Tool(google_search=genai.types.GoogleSearch())
        config = genai.types.GenerateContentConfig(tools=[grounding_tool])
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=config,
        )
        text = None
        if hasattr(response, "text") and response.text:
            text = (response.text or "").strip()
        elif response.candidates and response.candidates[0].content.parts:
            text = (response.candidates[0].content.parts[0].text or "").strip()
        return text or None
    except Exception as e:
        logger.warning("Market context (Gemini) failed: %s", e)
        return None
