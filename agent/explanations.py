"""
AI agent: given event and index snapshots, produce a short explanation of what drove the index.
"""
import json
import os
from typing import Any


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
