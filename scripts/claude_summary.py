"""Send raw stock + news data to Claude and ask for a structured morning digest."""
from __future__ import annotations

import json
import os
import re

from anthropic import Anthropic


MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")


SYSTEM_PROMPT = """You are a sharp, concise morning briefing writer for an Australian investor based in Brisbane.

You write a daily digest that helps the reader make informed decisions about their share portfolio
and stay across Australian politics, the AI industry, and major sport — without wasting their time.

Tone: plain English, opinionated but not reckless, honest when something is uncertain. No fluff,
no clickbait, no hedging clichés ("it remains to be seen"). Aussie-friendly phrasing.

Output STRICT JSON matching this shape:

{
  "headline": "<one sentence top-of-mind summary for the day>",
  "portfolio": {
    "summary": "<2-3 sentence overall portfolio read>",
    "movers": [
      { "ticker": "...", "name": "...", "change_pct": <number>, "note": "<one line: why it moved or what to watch>" }
    ]
  },
  "markets": {
    "summary": "<2-3 sentences on overnight global markets + commodities + AUD>",
    "indicators": [
      { "name": "...", "value": "...", "change_pct": <number>, "note": "<optional short note>" }
    ]
  },
  "politics": {
    "summary": "<2-4 sentences on what genuinely matters in Australian politics today>",
    "stories": [
      { "title": "...", "why_it_matters": "<one line>", "source": "...", "link": "..." }
    ]
  },
  "ai": {
    "summary": "<2-3 sentences on AI industry today>",
    "stories": [
      { "title": "...", "why_it_matters": "<one line>", "source": "...", "link": "..." }
    ]
  },
  "sport": {
    "summary": "<2-3 sentences covering NRL + major Aussie sport overnight>",
    "stories": [
      { "title": "...", "category": "NRL|Surfing|AFL|Tennis|Other", "source": "...", "link": "..." }
    ]
  },
  "watch_today": [
    { "title": "<short callout>", "detail": "<one line on what to watch or consider>" }
  ]
}

Rules:
- Include 3-6 portfolio movers (largest absolute moves first). If a holding didn't move much, you can skip it.
- For politics, AI, and sport: include 3-5 stories each. Drop anything that's just noise.
- "watch_today" should be 1-3 items. Skip the section (empty list) if nothing genuinely warrants attention.
- NEVER fabricate prices, percentages, links, or sources. Use only what's in the provided data.
- If a section has no usable data, return an empty stories list with a short summary explaining why.
- Output JSON only. No prose before or after."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def generate_digest(raw_data: dict) -> dict:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_content = (
        "Here is today's raw data. Write the digest as instructed.\n\n"
        f"```json\n{json.dumps(raw_data, indent=2, default=str)}\n```"
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    return _extract_json(text)
