"""Fetch weather for Gold Coast via Open-Meteo (free, no API key) — today + tomorrow."""
from __future__ import annotations

import requests


# Gold Coast, Queensland (Surfers Paradise area)
LAT = -28.0167
LON = 153.4000

# WMO weather codes → (human label, emoji)
WEATHER_CODES: dict[int, tuple[str, str]] = {
    0:  ("Clear sky",          "☀️"),
    1:  ("Mainly clear",       "🌤️"),
    2:  ("Partly cloudy",      "⛅"),
    3:  ("Overcast",           "☁️"),
    45: ("Fog",                "🌫️"),
    48: ("Freezing fog",       "🌫️"),
    51: ("Light drizzle",      "🌦️"),
    53: ("Drizzle",            "🌦️"),
    55: ("Heavy drizzle",      "🌦️"),
    56: ("Freezing drizzle",   "🌧️"),
    57: ("Freezing drizzle",   "🌧️"),
    61: ("Light rain",         "🌧️"),
    63: ("Rain",               "🌧️"),
    65: ("Heavy rain",         "🌧️"),
    66: ("Freezing rain",      "🌧️"),
    67: ("Freezing rain",      "🌧️"),
    71: ("Light snow",         "🌨️"),
    73: ("Snow",               "🌨️"),
    75: ("Heavy snow",         "🌨️"),
    77: ("Snow grains",        "🌨️"),
    80: ("Light showers",      "🌦️"),
    81: ("Scattered showers",  "🌦️"),
    82: ("Heavy showers",      "⛈️"),
    85: ("Snow showers",       "🌨️"),
    86: ("Snow showers",       "🌨️"),
    95: ("Thunderstorm",       "⛈️"),
    96: ("Storm with hail",    "⛈️"),
    99: ("Storm with hail",    "⛈️"),
}


def _at(arr, idx):
    if arr and idx < len(arr):
        return arr[idx]
    return None


def _round_or_none(val, ndigits=1):
    return round(val, ndigits) if val is not None else None


def _day_forecast(daily: dict, idx: int) -> dict:
    code = _at(daily.get("weather_code"), idx)
    label, icon = WEATHER_CODES.get(int(code), ("Unknown", "🌡️")) if code is not None else ("Unknown", "🌡️")
    high = _at(daily.get("temperature_2m_max"), idx)
    low = _at(daily.get("temperature_2m_min"), idx)
    chance = _at(daily.get("precipitation_probability_max"), idx)
    mm = _at(daily.get("precipitation_sum"), idx)
    return {
        "icon": icon,
        "condition": label,
        "high_c": _round_or_none(high),
        "low_c": _round_or_none(low),
        "rain_chance_pct": int(chance) if chance is not None else None,
        "rain_mm": _round_or_none(mm),
    }


def fetch_weather() -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,weather_code,precipitation"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code"
        "&timezone=Australia/Brisbane&forecast_days=2"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[weather] fetch failed: {e}")
        return {"location": "Gold Coast", "error": str(e)}

    current = data.get("current") or {}
    daily = data.get("daily") or {}

    # Current "now" conditions
    code_now = current.get("weather_code")
    if code_now is None:
        code_now = _at(daily.get("weather_code"), 0) or 0
    label_now, icon_now = WEATHER_CODES.get(int(code_now), ("Unknown", "🌡️"))
    temp = current.get("temperature_2m")

    today = _day_forecast(daily, 0)
    tomorrow = _day_forecast(daily, 1)

    return {
        "location": "Gold Coast",
        # current conditions (flat fields kept for backward compat)
        "icon": icon_now,
        "condition": label_now,
        "temperature_c": _round_or_none(temp),
        # today's day-forecast
        "high_c": today["high_c"],
        "low_c": today["low_c"],
        "rain_chance_pct": today["rain_chance_pct"],
        "rain_mm": today["rain_mm"],
        # tomorrow's full forecast (new)
        "tomorrow": tomorrow,
    }
