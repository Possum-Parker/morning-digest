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
from send_notification import send_push  # noqa: E402


BRISBANE = ZoneInfo("Australia/Brisbane")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def already_generated_today() -> bool:
    """True if data/latest.json was generated today (Brisbane local date)."""
    latest = ROOT / "data" / "latest.json"
    if not latest.exists():
        return False
    try:
        data = json.loads(latest.read_text())
        generated_iso = data.get("generated_at_utc")
        if not generated_iso:
            return False
        # tolerate both ...+00:00 and ...Z
        normalized = generated_iso.replace("Z", "+00:00")
        generated_utc = datetime.fromisoformat(normalized)
        generated_bne = generated_utc.astimezone(BRISBANE).date()
        today_bne = datetime.now(timezone.utc).astimezone(BRISBANE).date()
        return generated_bne == today_bne
    except Exception as e:
        print(f"[digest] idempotency check failed (will regenerate): {e}")
        return False


def gather_raw_data() -> dict:
    portfolio_cfg = _load_json(ROOT / "config" / "portfolio.json")
    topics_cfg = _load_json(ROOT / "config" / "topics.json")

    holdings = portfolio_cfg["holdings"]
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
    for key in ("australian_politics", "ai_world", "sport"):
        topic = topics_cfg[key]
        news[key] = fetch_topic(topic["queries"], exclude_keywords=topic.get("exclude_keywords", []))

    per_ticker_news: dict[str, list[dict]] = {}
    for ticker, queries in topics_cfg["portfolio_news"]["per_ticker_queries"].items():
        per_ticker_news[ticker] = fetch_topic(queries, per_query_max=3)

    weather = fetch_weather()
    nrl_info = fetch_nrl_draw()

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
    }


def main() -> int:
    if already_generated_today() and not os.environ.get("FORCE_GENERATE"):
        print("[digest] already generated today — skipping (set FORCE_GENERATE=1 to override).")
        return 0

    print("[digest] gathering raw data…")
    raw = gather_raw_data()
    print(
        f"[digest] got {len(raw['holdings'])} holdings, {len(raw['indicators'])} indicators, "
        f"{len(raw['nrl_draw'])} NRL fixtures, weather={'OK' if 'error' not in raw['weather'] else 'ERR'}."
    )

    print("[digest] calling Claude for summary…")
    digest = generate_digest(raw)

    # Merge in factual data Claude shouldn't fabricate
    digest["weather"] = raw["weather"]
    digest["nrl_round"] = raw["nrl_round"]
    digest["nrl_draw"] = raw["nrl_draw"]
    digest["nrl_byes"] = raw["nrl_byes"]
    digest["generated_at_utc"] = raw["generated_at_utc"]

    out_path = ROOT / "data" / "latest.json"
    out_path.write_text(json.dumps(digest, indent=2, ensure_ascii=False))
    print(f"[digest] wrote {out_path}")

    headline = digest.get("headline", "Your morning digest is ready.")
    send_push(headline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
