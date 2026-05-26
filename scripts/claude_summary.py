"""Send raw stock + news data to Claude and ask for a structured morning digest.

Uses Claude tool-use to guarantee valid JSON output matching the schema below.
"""
from __future__ import annotations

import json
import os

from anthropic import Anthropic


MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")


SYSTEM_PROMPT = """You are a sharp, concise end-of-day briefing writer for an Australian investor based on the Gold Coast.

The digest is delivered at ~5:30 PM AEST — so the ASX has just closed for the day, and the US markets
have NOT yet opened (they open ~11:30 PM AEST). Frame your writing accordingly:
  - For ASX holdings (.AX tickers, CBA, FUEL, VDHG, VGE, VTS): talk about "today's close" / "today's session".
  - For US holdings (GOOGL, MSFT, TTWO) and US indices (S&P, NASDAQ): the data is from "last night's session"
    (US markets traded overnight Brisbane time). Don't say "today" about US moves.
  - Australian politics and AI/sport news: cover what broke today during business hours.
  - "watch_today" can include things to watch in tonight's US session or tomorrow's ASX session.

Tone: plain English, opinionated but not reckless, honest when something is uncertain. No fluff,
no clickbait, no hedging clichés ("it remains to be seen"). Aussie-friendly phrasing is welcome.

Rules:
- Include 3-6 portfolio movers, largest absolute moves first. Skip holdings that didn't move much.
- For politics, AI, and sport: include 3-5 stories each. Drop anything that's just noise.
- "watch_today" should be 0-6 items. Each item MUST have an urgency:
    * "red"    = act / decide soon (e.g. major earnings tonight, sharp portfolio move, regulatory shock)
    * "orange" = something to watch this week (e.g. upcoming data print, building risk, news developing)
    * "green"  = informational / good-to-know (e.g. tailwind for a holding, useful background)
  Use an empty list if nothing genuinely warrants attention. Don't pad it for the sake of it.
- NEVER fabricate prices, percentages, links, or sources. Use only what's in the provided data.
- If a section has no usable data, return an empty stories list with a short summary explaining why.
- Weather and NRL draw are fetched separately and shown in the app — do NOT include them in your output.
  But you may reference them in your headline or watch_today if relevant (e.g. heavy rain affecting a surf event).

Call the submit_digest tool with the structured digest. Do not output any text — only the tool call."""


def _story_schema(extra_props: dict | None = None) -> dict:
    props = {
        "title": {"type": "string"},
        "why_it_matters": {"type": "string"},
        "source": {"type": "string"},
        "link": {"type": "string"},
    }
    if extra_props:
        props.update(extra_props)
    return {
        "type": "object",
        "properties": props,
        "required": ["title"],
    }


DIGEST_TOOL = {
    "name": "submit_digest",
    "description": "Submit the structured morning digest. Call this exactly once with all sections filled in.",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {
                "type": "string",
                "description": "One sentence top-of-mind summary for the day.",
            },
            "portfolio": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "movers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ticker": {"type": "string"},
                                "name": {"type": "string"},
                                "change_pct": {"type": "number"},
                                "note": {"type": "string"},
                            },
                            "required": ["ticker", "name", "change_pct", "note"],
                        },
                    },
                },
                "required": ["summary", "movers"],
            },
            "markets": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "indicators": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "value": {"type": "string"},
                                "change_pct": {"type": "number"},
                                "note": {"type": "string"},
                            },
                            "required": ["name", "value", "change_pct"],
                        },
                    },
                },
                "required": ["summary", "indicators"],
            },
            "politics": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "stories": {"type": "array", "items": _story_schema()},
                },
                "required": ["summary", "stories"],
            },
            "ai": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "stories": {"type": "array", "items": _story_schema()},
                },
                "required": ["summary", "stories"],
            },
            "sport": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "stories": {
                        "type": "array",
                        "items": _story_schema({"category": {"type": "string"}}),
                    },
                },
                "required": ["summary", "stories"],
            },
            "watch_today": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                        "urgency": {
                            "type": "string",
                            "enum": ["red", "orange", "green"],
                            "description": "red = act today, orange = watch this week, green = informational",
                        },
                    },
                    "required": ["title", "detail", "urgency"],
                },
            },
        },
        "required": ["headline", "portfolio", "markets", "politics", "ai", "sport", "watch_today"],
    },
}


def generate_digest(raw_data: dict) -> dict:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_content = (
        "Here is today's raw data. Write the digest by calling the submit_digest tool.\n\n"
        f"```json\n{json.dumps(raw_data, indent=2, default=str)}\n```"
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[DIGEST_TOOL],
        tool_choice={"type": "tool", "name": "submit_digest"},
        messages=[{"role": "user", "content": user_content}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_digest":
            return block.input

    raise ValueError(
        f"Claude did not return a submit_digest tool call. Stop reason: {response.stop_reason}. "
        f"Content blocks: {[b.type for b in response.content]}"
    )
