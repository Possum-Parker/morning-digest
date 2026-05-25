"""Fetch latest price + 1-day change for portfolio holdings and market indicators."""
from __future__ import annotations

import yfinance as yf


def _safe_pct(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None or prev == 0:
        return None
    return ((curr - prev) / prev) * 100


def fetch_quote(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    hist = t.history(period="5d", auto_adjust=False)
    if hist.empty:
        return {"ticker": ticker, "error": "no data"}

    last_close = float(hist["Close"].iloc[-1])
    prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None

    fast = getattr(t, "fast_info", {}) or {}
    currency = fast.get("currency") or "USD"

    return {
        "ticker": ticker,
        "price": round(last_close, 4),
        "previous_close": round(prev_close, 4) if prev_close is not None else None,
        "change": round(last_close - prev_close, 4) if prev_close is not None else None,
        "change_pct": round(_safe_pct(last_close, prev_close), 2) if prev_close is not None else None,
        "currency": currency,
    }


def fetch_all(tickers: list[str]) -> list[dict]:
    return [fetch_quote(t) for t in tickers]
