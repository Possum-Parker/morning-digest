"""Fetch weather forecast for Gold Coast via Open-Meteo (free, no API key)."""
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


def _first(arr, default=None):
    if arr and len(arr) > 0:
        return arr[0]
    return default


def fetch_weather() -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,weather_code,precipitation"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code"
        "&timezone=Australia/Brisbane&forecast_days=1"
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

    code = current.get("weather_code")
    if code is None:
        code = _first(daily.get("weather_code"), 0)
    label, icon = WEATHER_CODES.get(int(code), ("Unknown", "🌡️"))

    temp = current.get("temperature_2m")
    high = _first(daily.get("temperature_2m_max"))
    low = _first(daily.get("temperature_2m_min"))
    rain_chance = _first(daily.get("precipitation_probability_max"))
    rain_mm = _first(daily.get("precipitation_sum"))

    return {
        "location": "Gold Coast",
        "icon": icon,
        "condition": label,
        "temperature_c": round(temp, 1) if temp is not None else None,
        "high_c": round(high, 1) if high is not None else None,
        "low_c": round(low, 1) if low is not None else None,
        "rain_chance_pct": int(rain_chance) if rain_chance is not None else None,
        "rain_mm": round(rain_mm, 1) if rain_mm is not None else None,
    }
