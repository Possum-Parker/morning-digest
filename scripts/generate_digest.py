"""Orchestrator: fetch raw data, call Claude, write data/latest.json, send push."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from claude_summary import generate_digest  # noqa: E402
from fetch_news import fetch_topic  # noqa: E402
from fetch_nrl import fetch_nrl_draw  # noqa: E402
from fetch_stocks import fetch_all  # noqa: E402
from fetch_weather import fetch_weather  # noqa: E402
import portfolio_pnl  # noqa: E402
from send_notification import send_push  # noqa: E402


BRISBANE = ZoneInfo("Australia/Brisbane")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


IDEMPOTENCY_WINDOW_HOURS = 4


def recently_generated() -> bool:
    """True if data/latest.json was generated in the last IDEMPOTENCY_WINDOW_HOURS hours.

    Why hours, not "today": the daily-digest workflow has 4 staggered cron times (5:30,
    5:50, 6:15, 6:45 PM AEST) for reliability — we want only the FIRST of those to
    actually generate, not all of them. But if we used "today" instead of "hours", a
    manual test run earlier in the day would suppress the 5:30 PM scheduled run, which
    would mean no push notification at the user's expected time. 4 hours is comfortably
    longer than the cron fallback window (~75 min) but short enough that a manual
    morning/afternoon test doesn't block the evening's scheduled run.
    """
    latest = ROOT / "data" / "latest.json"
    if not latest.exists():
        return False
    try:
        data = json.loads(latest.read_text())
        generated_iso = data.get("generated_at_utc")
        if not generated_iso:
            return False
        normalized = generated_iso.replace("Z", "+00:00")
        generated_utc = datetime.fromisoformat(normalized)
        age_hours = (datetime.now(timezone.utc) - generated_utc).total_seconds() / 3600
        return age_hours < IDEMPOTENCY_WINDOW_HOURS
    except Exception as e:
        print(f"[digest] idempotency check failed (will regenerate): {e}")
        return False


def gather_raw_data() -> dict:
    portfolio_cfg = _load_json(ROOT / "config" / "portfolio.json")
    topics_cfg = _load_json(ROOT / "config" / "topics.json")

    # holdings.json is the single source of truth for what the user actually owns.
    # We only track/price/comment on tickers present there — so selling a stock
    # (removing it from holdings.json) makes it vanish from the whole digest,
    # including Watch Today. portfolio.json just supplies metadata + news queries.
    owned = portfolio_pnl.load_holdings()
    # A holding counts as "owned" only if it has a positive share count — zeroing out
    # a position via the edit form is treated the same as selling it entirely.
    owned_tickers = {t for t, h in owned.items() if float(h.get("shares") or 0) > 0}

    all_holdings = portfolio_cfg["holdings"]
    if owned_tickers:
        holdings = [h for h in all_holdings if h["ticker"] in owned_tickers]
        skipped = [h["ticker"] for h in all_holdings if h["ticker"] not in owned_tickers]
        if skipped:
            print(f"[digest] skipping non-owned tickers (not in holdings.json): {skipped}")
    else:
        # No holdings file → fall back to tracking everything in portfolio.json
        print("[digest] holdings.json empty/missing — tracking all portfolio.json tickers")
        holdings = all_holdings

    indicators = portfolio_cfg["market_indicators"]

    holdings_quotes = fetch_all([h["yfinance"] for h in holdings])
    by_ticker = {h["yfinance"]: h for h in holdings}
    for q in holdings_quotes:
        meta = by_ticker.get(q["ticker"], {})
        q["name"] = meta.get("name", q["ticker"])
        q["exchange"] = meta.get("exchange", "")

    indicator_quotes = fetch_all([i["ticker"] for i in indicators])
    by_indicator = {i["ticker"]: i for i in indicators}
    for q in indicator_quotes:
        q["name"] = by_indicator.get(q["ticker"], {}).get("name", q["ticker"])

    news: dict[str, list[dict]] = {}
    for key in ("world_news", "australian_politics", "ai_world", "sport"):
        topic = topics_cfg.get(key)
        if not topic:
            continue
        news[key] = fetch_topic(topic["queries"], exclude_keywords=topic.get("exclude_keywords", []))

    # Only fetch per-ticker news for tickers the user still owns
    per_ticker_news: dict[str, list[dict]] = {}
    for ticker, queries in topics_cfg["portfolio_news"]["per_ticker_queries"].items():
        if owned_tickers and ticker not in owned_tickers:
            continue
        per_ticker_news[ticker] = fetch_topic(queries, per_query_max=3)

    weather = fetch_weather()
    nrl_info = fetch_nrl_draw()

    # Compute portfolio P&L from holdings file + the prices we just fetched
    aud_usd_rate = None
    for q in indicator_quotes:
        if q.get("ticker") == "AUDUSD=X" and q.get("price"):
            aud_usd_rate = float(q["price"])
            break
    holdings_data = portfolio_pnl.load_holdings()
    pnl = portfolio_pnl.compute(holdings_data, holdings_quotes, aud_usd_rate)
    print(
        f"[pnl] {len(pnl['positions'])} positions, "
        f"total value ${pnl['total_value_aud']:.2f} AUD, "
        f"P&L ${pnl['total_pnl_aud']:.2f} ({pnl['total_pnl_pct']}%)"
    )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "weather": weather,
        "nrl_round": nrl_info.get("round_label", ""),
        "nrl_draw": nrl_info.get("fixtures", []),
        "nrl_byes": nrl_info.get("byes", []),
        "holdings": holdings_quotes,
        "indicators": indicator_quotes,
        "news": news,
        "portfolio_news": per_ticker_news,
        "portfolio_pnl": pnl,
    }


def main() -> int:
    if recently_generated() and not os.environ.get("FORCE_GENERATE"):
        print(f"[digest] already generated within the last {IDEMPOTENCY_WINDOW_HOURS}h — skipping.")
        return 0

    print("[digest] gathering raw data…")
    raw = gather_raw_data()
    print(
        f"[digest] got {len(raw['holdings'])} holdings, {len(raw['indicators'])} indicators, "
        f"{len(raw['nrl_draw'])} NRL fixtures, weather={'OK' if 'error' not in raw['weather'] else 'ERR'}."
    )

    print("[digest] calling Claude for summary…")
    digest = generate_digest(raw)

    # Defensive: ensure optional sections always exist so the frontend never breaks
    digest.setdefault("watch_today", [])
    if not digest.get("watch_today"):
        print("[digest] WARNING: watch_today came back empty.")
    digest.setdefault("world", {"summary": "", "stories": []})

    # Merge in factual data Claude shouldn't fabricate
    digest["weather"] = raw["weather"]
    digest["nrl_round"] = raw["nrl_round"]
    digest["nrl_draw"] = raw["nrl_draw"]
    digest["nrl_byes"] = raw["nrl_byes"]
    digest["portfolio_totals"] = raw["portfolio_pnl"]
    digest["generated_at_utc"] = raw["generated_at_utc"]

    out_path = ROOT / "data" / "latest.json"
    out_path.write_text(json.dumps(digest, indent=2, ensure_ascii=False))
    print(f"[digest] wrote {out_path}")

    headline = digest.get("headline", "Your morning digest is ready.")
    send_push(headline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
