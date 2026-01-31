#!/usr/bin/env python3
"""
Standalone script to play with the Gemini API.
Run from project root: python scripts/play_gemini.py
Set GEMINI_API_KEY in env or pass as first arg.
"""
import json
import os
import sys


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not api_key:
        print("Set GEMINI_API_KEY or pass it as first arg: python scripts/play_gemini.py YOUR_KEY")
        sys.exit(1)

    try:
        from google import genai
    except ImportError:
        print("Install: pip install google-genai")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Example: given event name and URL, which tools would you use?
    event_name = "Cursor Hackathon Dec 24"
    source_url = "https://reddit.com/r/cursor/comments/abc123"
    prompt = f"""Given this event for an attention-tracking system:
- Event name: {event_name}
- Source URL: {source_url}

Available tools (id, description):
- hn_frontpage: Fetches Hacker News front page RSS; counts items matching keywords.
- reddit: Fetches Reddit subreddit or post (placeholder).

Reply with a JSON object only: {{ "tools": ["hn_frontpage", "reddit"], "keywords": ["cursor", "hackathon"], "exclusions": [] }}
Which tools would you use and what keywords? Output only valid JSON, no markdown."""

    print("Sending to Gemini...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    text = response.text if hasattr(response, "text") else (response.candidates[0].content.parts[0].text if response.candidates else "")
    print("Response:", text)
    # Try to parse as JSON
    text_clean = text.strip()
    if text_clean.startswith("```"):
        text_clean = text_clean.split("\n", 1)[1] if "\n" in text_clean else text_clean[3:]
    if text_clean.endswith("```"):
        text_clean = text_clean.rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(text_clean)
        print("Parsed JSON:", json.dumps(parsed, indent=2))
    except json.JSONDecodeError:
        print("(Could not parse as JSON)")


if __name__ == "__main__":
    main()
