"""Fetch latest price + 1-day change for portfolio holdings and market indicators.

Yahoo Finance blocks bare HTTP requests from data-centre IPs (including GitHub Actions
runners). We work around this with curl_cffi, which performs the TLS handshake with the
same fingerprint as a real Chrome browser, so Yahoo treats the requests as legitimate.
"""
from __future__ import annotations

import time

import yfinance as yf

try:
    from curl_cffi import requests as curl_requests
    _SESSION = curl_requests.Session(impersonate="chrome")
except Exception as e:  # pragma: no cover
    print(f"[stocks] curl_cffi unavailable, falling back to default session: {e}")
    _SESSION = None


def _safe_pct(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None or prev == 0:
        return None
    return ((curr - prev) / prev) * 100


def fetch_quote(ticker: str, *, retries: int = 2) -> dict:
    last_err: str | None = None
    for attempt in range(retries + 1):
        try:
            t = yf.Ticker(ticker, session=_SESSION) if _SESSION else yf.Ticker(ticker)
            hist = t.history(period="5d", auto_adjust=False)
            if hist.empty:
                last_err = "empty history"
            else:
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
        except Exception as e:
            last_err = str(e)

        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))

    print(f"[stocks] failed to fetch {ticker}: {last_err}")
    return {"ticker": ticker, "error": last_err or "unknown"}


def fetch_all(tickers: list[str]) -> list[dict]:
    return [fetch_quote(t) for t in tickers]
