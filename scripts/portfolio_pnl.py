"""Compute portfolio P&L from holdings + live price quotes.

Holdings live in config/holdings.json as { ticker: { shares, total_invested } }.
For ASX tickers (.AX), total_invested is in AUD. For US tickers, it's in USD.
We aggregate everything in AUD for the portfolio total, using the current AUD/USD rate.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_holdings() -> dict:
    path = ROOT / "config" / "holdings.json"
    if not path.exists():
        print("[pnl] no config/holdings.json found")
        return {}
    return json.loads(path.read_text())


def _ticker_currency(ticker: str) -> str:
    return "AUD" if ticker.endswith(".AX") else "USD"


def compute(
    holdings: dict,
    quotes: list[dict],
    aud_usd_rate: float | None,
) -> dict:
    """Returns { positions: [...], total_invested_aud, total_value_aud, total_pnl_aud, total_pnl_pct }."""
    if not aud_usd_rate or aud_usd_rate <= 0:
        print(f"[pnl] warning: no AUD/USD rate available, using fallback 0.66")
        aud_usd_rate = 0.66

    quotes_by_ticker = {q.get("ticker"): q for q in quotes if q.get("ticker")}

    positions: list[dict] = []
    total_invested_aud = 0.0
    total_value_aud = 0.0

    for ticker, holding in holdings.items():
        shares = float(holding.get("shares") or 0)
        # A zeroed-out holding means the user sold it — skip it entirely.
        if shares <= 0:
            continue
        invested_native = float(holding.get("total_invested") or 0)
        currency = _ticker_currency(ticker)
        quote = quotes_by_ticker.get(ticker)

        invested_aud = invested_native if currency == "AUD" else invested_native / aud_usd_rate

        if not quote or quote.get("error") or not shares or quote.get("price") in (None, 0):
            positions.append({
                "ticker": ticker,
                "shares": shares,
                "currency": currency,
                "current_price": None,
                "current_value_native": None,
                "current_value_aud": None,
                "total_invested": round(invested_native, 2),
                "total_invested_aud": round(invested_aud, 2),
                "pnl_native": None,
                "pnl_aud": None,
                "pnl_pct": None,
                "day_change_pct": None,
            })
            total_invested_aud += invested_aud
            continue

        price = float(quote["price"])
        value_native = shares * price
        value_aud = value_native if currency == "AUD" else value_native / aud_usd_rate

        pnl_native = value_native - invested_native
        pnl_aud = value_aud - invested_aud
        pnl_pct = (pnl_native / invested_native * 100) if invested_native > 0 else None

        day_change = quote.get("change_pct")

        positions.append({
            "ticker": ticker,
            "shares": round(shares, 4),
            "currency": currency,
            "current_price": round(price, 4),
            "current_value_native": round(value_native, 2),
            "current_value_aud": round(value_aud, 2),
            "total_invested": round(invested_native, 2),
            "total_invested_aud": round(invested_aud, 2),
            "pnl_native": round(pnl_native, 2),
            "pnl_aud": round(pnl_aud, 2),
            "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
            "day_change_pct": round(float(day_change), 2) if day_change is not None else None,
        })

        total_invested_aud += invested_aud
        total_value_aud += value_aud

    total_pnl_aud = total_value_aud - total_invested_aud
    total_pnl_pct = (total_pnl_aud / total_invested_aud * 100) if total_invested_aud > 0 else None

    return {
        "positions": positions,
        "total_invested_aud": round(total_invested_aud, 2),
        "total_value_aud": round(total_value_aud, 2),
        "total_pnl_aud": round(total_pnl_aud, 2),
        "total_pnl_pct": round(total_pnl_pct, 2) if total_pnl_pct is not None else None,
        "aud_usd_rate": round(aud_usd_rate, 4),
    }
