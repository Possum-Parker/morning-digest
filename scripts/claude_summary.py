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
  - World news, Australian politics, AI, and sport news: cover what broke today.

SECTIONS & BALANCE — this digest is NOT just about shares. Give real weight to what's happening in the
world. The `world` section is a major part of the briefing, not an afterthought:
  - `world`: the big global stories today — international politics, conflicts, elections, major economic
    or humanitarian events, significant world developments. Aim for 4-5 substantial stories. Explain
    what happened and why it matters to an everyday person, in plain English. This is the reader's window
    onto the world beyond finance — treat it as importantly as the portfolio.
  - `politics`: Australian domestic politics & economy specifically.
  - Keep world (global) and politics (Australian) distinct — don't duplicate stories across them.

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

SPECIFICITY — every story's "why_it_matters" must be SELF-CONTAINED:
  - The reader should learn the actual important facts WITHOUT clicking the link.
  - Many stories include a "text" field with the actual article body. USE IT. Pull out names,
    numbers, scores, percentages, quotes — don't just paraphrase the title.
  - Bad: "Big injury news heading into Round 13 — the Warriors have lost a key player".
  - Good: "Warriors lose Mitchell Barnett (knee, 6 weeks) and Wayde Egan (concussion). Tigers
    without Jahream Bula (suspended). Big blow for both clubs heading into Round 13."
  - Bad: "Labor to tie tax cuts to CGT reform".
  - Good: "Labor wants to fund $4,500 tax cuts for under-$135k earners by raising the capital
    gains tax discount from 50% to 25% and tightening negative gearing on existing properties.
    Property investors hit hardest. Treasury modelling expected Friday."
  - Aim for 2-4 sentences per why_it_matters, packed with actual facts from the article text.
  - If the article text isn't available (no "text" field), be honest and brief rather than vague.

WATCH TODAY (watch_today) — THIS IS THE MOST IMPORTANT SECTION. NEVER leave it empty.
  Always return 3-6 watch_today items. This is the headline takeaway the user opens the app for.
  ONLY make buy/hold/sell recommendations for tickers that appear in the `portfolio_pnl` positions
  list in the raw data — those are the ONLY stocks the user currently owns. If a ticker is NOT in
  that list, the user has sold it — do NOT mention it or give any recommendation about it.
  When you see a signal in the news or price data relevant to one of the user's CURRENT holdings,
  include an explicit recommendation by setting "action" to "buy", "hold", or "sell" and "ticker".
  - Be honest. If there's no strong signal on a ticker, "hold" is the right call — but still include it.
  - At least 2-3 of your items should carry a buy/hold/sell action on a specific holding.
  - Use the "detail" field to explain WHY in plain English (the news, the price action, the catalyst).
  - You can also include non-action watch items (no action/ticker) for general things to keep an eye on
    (e.g. "RBA decision Tuesday", "oil spiking on Middle East tension").

  INVESTOR STYLE — THE READER IS A LONG-TERM BUY-AND-HOLD INVESTOR. Frame every recommendation
  through that lens. He buys shares to hold for years, isn't taking earnings/income now, and is NOT
  a day trader.
  - "hold" should be your DEFAULT and by far your most common call. A bad night or a single-day dip
    is NEVER a reason to sell — for a long-term holder it's noise, and often a buying opportunity.
  - Only say "sell" for genuinely serious, structural reasons (e.g. the long-term investment thesis is
    broken, a company is in real trouble, an accounting scandal) — not short-term price weakness.
    Selling should be rare. When in doubt, it's "hold".
  - "buy" means "this dip/news could be a good moment to add for the long term" — frame it as topping up
    a long-term position, not chasing a quick trade.
  - Reassure on volatility: when a holding drops, if the long-term story is intact, say so plainly
    (e.g. "down tonight but nothing's changed with the long-term case — sit tight").

URGENCY (every watch_today item must have one):
  * "red"    = act / decide soon (e.g. earnings tonight US time, sharp portfolio move, regulatory shock)
  * "orange" = something to watch this week (e.g. building risk, news developing, upcoming data print)
  * "green"  = informational / good-to-know (e.g. tailwind for a holding, useful background)

PORTFOLIO MOVERS (portfolio.movers):
  The raw data includes a `portfolio_pnl` block with real dollar amounts:
    - Each position has shares, current_value_aud, total_invested_aud, pnl_aud (in AUD), pnl_pct
  For each notable holding, write a `note` explaining WHY it moved in its last session — this is shown
  as a "Why it moved" dropdown under each holding in the app. There is NO portfolio summary anymore,
  so all portfolio commentary lives in these per-holding notes and in watch_today.
  - Speak plainly. Explain the actual cause: "GOOG fell because the market is favouring Microsoft's AI story".
  - Keep each note to 1-3 sentences. Be specific about the catalyst when the news data supports it.

Rules:
- Include a mover entry for EVERY holding that has price data (so each gets a "why it moved" note),
  ordered by largest absolute move first.
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
                "required": ["movers"],
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
                            "description": "Optional. The ticker the action applies to (e.g. GOOG, PLS.AX).",
                        },
                    },
                    "required": ["title", "detail", "urgency"],
                },
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
            "world": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "stories": {"type": "array", "items": _story_schema()},
                },
                "required": ["summary", "stories"],
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
        },
        "required": ["headline", "portfolio", "watch_today", "world", "markets", "politics", "ai", "sport"],
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
        max_tokens=16000,
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
