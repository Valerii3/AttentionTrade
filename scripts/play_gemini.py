#!/usr/bin/env python3
"""
Standalone script to play with the Gemini API.
Run from project root: python scripts/play_gemini.py
Set GEMINI_API_KEY in env or pass as first arg.
"""
import json
import os
import sys

from google import genai


client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

for m in client.models.list():
    print(m.name)

grounding_tool = genai.types.Tool(
    google_search=genai.types.GoogleSearch()
)

config = genai.types.GenerateContentConfig(
    tools=[grounding_tool]
)


response = client.models.generate_content(
    model="gemini-2.5-flash-lite",
    contents="What do u know about cursor hack in hamburg?",
    #=[{"type": "google_search"}]
    config=config
)

print(response.text)
