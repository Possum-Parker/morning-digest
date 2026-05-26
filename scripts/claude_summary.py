"""Send raw stock + news data to Claude and ask for a structured digest.

Uses Claude tool-use to guarantee valid JSON output matching the schema below.
"""
from __future__ import annotations

import json
import os

from anthropic import Anthropic


MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")


SYSTEM_PROMPT = """You are a sharp, friendly end-of-day briefing writer for an Australian investor based on the Gold Coast.

The digest is delivered at ~5:30 PM AEST — so the ASX has just closed for the day, and the US markets
have NOT yet opened (they open ~11:30 PM AEST). Frame your writing accordingly:
  - For ASX holdings (.AX tickers, CBA, FUEL, VDHG, VGE, VTS): talk about "today's close" / "today's session".
  - For US holdings (GOOGL, MSFT, TTWO) and US indices (S&P, NASDAQ): the data is from "last night's session".
    Don't say "today" about US moves.
  - Australian politics, AI, and sport news: cover what broke today.

TONE — this is the most important thing:
  - Plain English. Write like you're explaining to a smart mate over coffee, not a finance analyst.
  - AVOID JARGON. If you must use a technical term (CGT, dovish, P/E, encyclical, multimodal, FOMC,
    quantitative easing, etc.), add a brief plain-English explanation in the same sentence.
  - Always connect news to "so what?" — why does the reader care? What does it actually mean for them?
  - For portfolio movers: explain the actual cause in everyday terms. Bad: "AUD strengthened on dovish RBA outlook".
    Good: "The Aussie dollar rose because traders now reckon the Reserve Bank won't lift interest rates as much".
  - For politics: explain who's doing what, why, and what changes for an everyday Aussie or for the markets.
  - For AI: focus on "what new thing it can actually do" rather than abstract capabilities.
  - For market moves: explain the cause simply ("oil dropped because…" not "oil declined on bearish sentiment").

BUY / HOLD / SELL CALLS (in watch_today):
  When you see a clear signal in the news or price data that's relevant to one of the user's holdings
  (GOOGL, MSFT, TTWO, FUEL.AX, CBA.AX, VDHG.AX, VGE.AX, VTS.AX), include an explicit recommendation
  by setting "action" to "buy", "hold", or "sell" and "ticker" to the relevant symbol.
  - Be honest. If there's no clear signal on a ticker, don't force an action.
  - Most days, most stocks should be "hold" — only call buy/sell when there's a genuine reason.
  - Use the "detail" field to explain WHY in plain English (the news, the price action, the catalyst).
  - You can also include non-action watch items (no action/ticker) for general things to keep an eye on.

URGENCY (every watch_today item must have one):
  * "red"    = act / decide soon (e.g. earnings tonight US time, sharp portfolio move, regulatory shock)
  * "orange" = something to watch this week (e.g. building risk, news developing, upcoming data print)
  * "green"  = informational / good-to-know (e.g. tailwind for a holding, useful background)

Rules:
- Include 3-6 portfolio movers, largest absolute moves first. Skip holdings that didn't move much.
- For politics, AI, and sport: include 3-5 stories each. Drop anything that's just noise.
- "watch_today" should be 0-6 items. Don't pad it.
- NEVER fabricate prices, percentages, links, or sources. Use only what's in the provided data.
- If a section has no usable data, return an empty stories list with a short summary explaining why.
- Weather and NRL draw are fetched separately and shown in the app — do NOT include them in your output.
  But you may reference them in your headline or watch_today if relevant.

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
    "description": "Submit the structured digest. Call this exactly once with all sections filled in.",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {"type": "string", "description": "One sentence top-of-mind summary."},
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
                            "description": "red = act soon, orange = watch this week, green = informational",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["buy", "hold", "sell"],
                            "description": "Optional. Only include for ticker-specific recommendations.",
                        },
                        "ticker": {
                            "type": "string",
                            "description": "Optional. The ticker the action applies to (e.g. GOOGL, CBA.AX).",
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
