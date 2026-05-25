"""Fetch NRL fixtures for the week ahead via TheSportsDB (free, no API key)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests


NRL_LEAGUE_ID = 4435  # National Rugby League on TheSportsDB
BRISBANE = ZoneInfo("Australia/Brisbane")


def _format_time(dt) -> str:
    # "7:50 pm" — strip leading zero on hour
    return dt.strftime("%I:%M %p").lstrip("0").lower()


def fetch_nrl_draw(*, days_ahead: int = 8) -> list[dict]:
    url = f"https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id={NRL_LEAGUE_ID}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        events = (r.json() or {}).get("events") or []
    except Exception as e:
        print(f"[nrl] fetch failed: {e}")
        return []

    cutoff = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    fixtures: list[dict] = []

    for ev in events:
        date_s = ev.get("dateEvent")
        time_s = ev.get("strTime") or "00:00:00"
        if not date_s:
            continue
        try:
            dt_utc = datetime.fromisoformat(f"{date_s}T{time_s}").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if dt_utc > cutoff:
            continue

        dt_bne = dt_utc.astimezone(BRISBANE)
        fixtures.append({
            "home": ev.get("strHomeTeam") or "TBC",
            "away": ev.get("strAwayTeam") or "TBC",
            "day": dt_bne.strftime("%a %d %b"),         # "Fri 30 May"
            "time": _format_time(dt_bne),               # "7:50 pm"
            "venue": ev.get("strVenue") or "",
            "datetime_iso": dt_bne.isoformat(),
        })

    fixtures.sort(key=lambda f: f["datetime_iso"])
    return fixtures
