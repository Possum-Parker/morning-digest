"""Fetch NRL fixtures for the CURRENT ROUND ONLY, with live scores overlaid.

Logic:
  1. Load the static draw JSON (parsed from the official NRL PDF — see
     scripts/parse_nrl_pdf.py).
  2. Determine the current round = the earliest round whose last match date
     is still >= today's Brisbane date. This means:
       - Mon-Wed: shows the upcoming round (its games start Thu/Fri).
       - Thu-Sun: shows that round as it plays out.
       - Once Sunday night's last game has passed, Monday rolls over to the next round.
  3. For each match in the current round, fetch live API scores from TheSportsDB
     and overlay them. Games that haven't been played yet just show the kickoff time.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


ROOT = Path(__file__).resolve().parent.parent
NRL_LEAGUE_ID = 4435
BRISBANE = ZoneInfo("Australia/Brisbane")
SYDNEY = ZoneInfo("Australia/Sydney")  # PDF "AEDT" column == Sydney local time
API_KEY = os.environ.get("THESPORTSDB_KEY", "3")
BASE = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"


# Multi-word nicknames first so they match before single-word ones
NICKNAMES = [
    "sea eagles",
    "broncos", "bulldogs", "cowboys", "dolphins", "dragons", "eels",
    "knights", "panthers", "rabbitohs", "raiders", "roosters", "sharks",
    "storm", "tigers", "titans", "warriors",
]

WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty-one": 21, "twenty one": 21,
    "twenty-two": 22, "twenty two": 22,
    "twenty-three": 23, "twenty three": 23,
    "twenty-four": 24, "twenty four": 24,
    "twenty-five": 25, "twenty five": 25,
    "twenty-six": 26, "twenty six": 26,
    "twenty-seven": 27, "twenty seven": 27,
}


def _normalize_team(name: str) -> str:
    s = (name or "").lower().strip()
    for nick in NICKNAMES:
        if s.endswith(nick):
            return nick
    return s


def _round_to_number(round_name: str):
    if not round_name:
        return None
    s = round_name.strip().lower()
    if s.isdigit():
        return int(s)
    return WORD_TO_NUM.get(s)


def _format_time(dt) -> str:
    return dt.strftime("%I:%M %p").lstrip("0").lower()


def _fixture_key(date_str: str, home: str, away: str) -> str:
    return f"{date_str[:10]}|{_normalize_team(home)}|{_normalize_team(away)}"


# ---------- TheSportsDB (for live scores only) ----------

def _get(endpoint: str, params: dict | None = None) -> dict:
    try:
        r = requests.get(f"{BASE}/{endpoint}", params=params or {}, timeout=15)
        print(f"[nrl] GET {endpoint} {params or {}} -> {r.status_code}")
        r.raise_for_status()
        return r.json() or {}
    except Exception as e:
        print(f"[nrl]   FAILED: {e}")
        return {}


def _fetch_team_badges() -> dict[str, str]:
    data = _get("lookup_all_teams.php", {"id": NRL_LEAGUE_ID})
    teams = data.get("teams") or []
    badges: dict[str, str] = {}
    for t in teams:
        nick = _normalize_team(t.get("strTeam") or "")
        badge = t.get("strBadge") or t.get("strTeamBadge") or ""
        if nick and badge:
            badges[nick] = badge
    print(f"[nrl]   badges loaded: {len(badges)}")
    return badges


def _fetch_api_scores() -> dict[str, dict]:
    """Returns {fixture_key: {home_score, away_score, completed}} from TheSportsDB."""
    year = str(datetime.now(BRISBANE).year)
    events = (
        (_get("eventsseason.php", {"id": NRL_LEAGUE_ID, "s": year}).get("events") or [])
        + (_get("eventspastleague.php", {"id": NRL_LEAGUE_ID}).get("events") or [])
        + (_get("eventsnextleague.php", {"id": NRL_LEAGUE_ID}).get("events") or [])
    )
    scores: dict[str, dict] = {}
    for ev in events:
        date_s = ev.get("dateEvent")
        home = ev.get("strHomeTeam")
        away = ev.get("strAwayTeam")
        if not date_s or not home or not away:
            continue
        hs = ev.get("intHomeScore")
        as_ = ev.get("intAwayScore")
        completed = hs not in (None, "") and as_ not in (None, "")
        if not completed:
            continue
        key = _fixture_key(date_s, home, away)
        scores[key] = {
            "home_score": int(hs),
            "away_score": int(as_),
            "completed": True,
        }
    print(f"[nrl] API: {len(scores)} completed games with scores")
    return scores


# ---------- Static draw (the source of truth for fixtures) ----------

def _load_static() -> dict | None:
    year = datetime.now(BRISBANE).year
    for path in (
        ROOT / "config" / f"nrl_draw_{year}.json",
        ROOT / "config" / f"nrl_draw_{year - 1}.json",
    ):
        if path.exists():
            print(f"[nrl] static draw: {path.name}")
            return json.loads(path.read_text())
    print("[nrl] no static draw JSON found")
    return None


def _parse_static_time(date_str: str, time_str: str):
    """Static draw's time is Sydney-local (AEDT column). Convert to Brisbane."""
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None
    ts = (time_str or "").strip().upper()
    if not ts or ts == "TBC":
        return d.replace(hour=0, minute=0, tzinfo=SYDNEY).astimezone(BRISBANE)
    try:
        clean = ts.replace(" ", "")
        ampm = "PM"
        if clean.endswith("AM"):
            clean, ampm = clean[:-2], "AM"
        elif clean.endswith("PM"):
            clean, ampm = clean[:-2], "PM"
        h, m = clean.split(":")
        h, m = int(h), int(m)
        if ampm == "PM" and h < 12:
            h += 12
        if ampm == "AM" and h == 12:
            h = 0
        return d.replace(hour=h, minute=m, tzinfo=SYDNEY).astimezone(BRISBANE)
    except Exception:
        return None


def _find_current_round(static_data: dict, today_bne_date):
    """Return the round whose last match date is the earliest still >= today."""
    candidates = []
    for r in static_data.get("rounds") or []:
        dates = []
        for m in r.get("matches") or []:
            try:
                dates.append(datetime.strptime(m["date"], "%Y-%m-%d").date())
            except Exception:
                pass
        if not dates:
            continue
        last = max(dates)
        if last >= today_bne_date:
            candidates.append((last, r))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


# ---------- Public entrypoint ----------

def fetch_nrl_draw() -> dict:
    """Returns {round_label, fixtures, byes}."""
    static_data = _load_static()
    if not static_data:
        return {"round_label": "", "fixtures": [], "byes": []}

    today_bne = datetime.now(BRISBANE).date()
    current = _find_current_round(static_data, today_bne)
    if not current:
        print("[nrl] no upcoming round in static draw (off-season?)")
        return {"round_label": "Off-Season", "fixtures": [], "byes": []}

    round_name = (current.get("round") or "").strip()
    round_num = _round_to_number(round_name)
    round_label = f"Round {round_num}" if round_num else (f"Round {round_name}" if round_name else "")
    byes = current.get("byes") or []

    badges = _fetch_team_badges()
    api_scores = _fetch_api_scores()

    fixtures: list[dict] = []
    for m in current.get("matches") or []:
        date_str = m.get("date", "")
        time_str = (m.get("aedt_time") or "").strip()
        dt_bne = _parse_static_time(date_str, time_str)
        if not dt_bne:
            continue

        home = m.get("home") or "TBC"
        away = m.get("away") or "TBC"
        key = _fixture_key(date_str, home, away)

        fixture = {
            "home": home,
            "away": away,
            "home_badge": badges.get(_normalize_team(home), ""),
            "away_badge": badges.get(_normalize_team(away), ""),
            "home_score": None,
            "away_score": None,
            "completed": False,
            "day": dt_bne.strftime("%a %d %b"),
            "time": "TBC" if time_str.upper() == "TBC" else _format_time(dt_bne),
            "venue": m.get("venue") or "",
            "datetime_iso": dt_bne.isoformat(),
        }

        score = api_scores.get(key)
        if score:
            fixture.update(score)

        fixtures.append(fixture)

    fixtures.sort(key=lambda f: f["datetime_iso"])
    print(f"[nrl] {round_label}: {len(fixtures)} fixtures, byes={byes}")

    return {"round_label": round_label, "fixtures": fixtures, "byes": byes}
