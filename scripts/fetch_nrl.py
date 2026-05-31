"""Fetch NRL fixtures for the CURRENT ROUND ONLY, with live scores.

Primary source: NRL.com's public JSON draw endpoint. It auto-returns the current round,
includes live scores + match state (FullTime / SecondHalf / Upcoming / etc.), team
theme keys for badges, and proper UTC kickoff times. This is the canonical source.

Fallback: the static draw parsed from the NRL's official PDF
(config/nrl_draw_{year}.json). Has fixtures but no scores — only used if NRL.com is
unreachable.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


ROOT = Path(__file__).resolve().parent.parent
BRISBANE = ZoneInfo("Australia/Brisbane")
SYDNEY = ZoneInfo("Australia/Sydney")  # PDF "AEDT" column == Sydney local

NRL_DRAW_URL = "https://www.nrl.com/draw/data"
NRL_COMP_ID = 111  # NRL Premiership
NRL_THEME_BASE = "https://www.nrl.com/.theme"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nrl.com/draw/",
}

# matchState values from NRL.com → human label shown in UI
LIVE_STATES = {"FirstHalf": "1st Half", "SecondHalf": "2nd Half", "HalfTime": "Half Time"}
COMPLETED_STATES = {"FullTime", "PostMatch", "PostGame"}


def _format_time(dt) -> str:
    """'7:50 pm' — strip leading zero on hour."""
    return dt.strftime("%I:%M %p").lstrip("0").lower()


def _theme_badge(theme_key: str) -> str:
    if not theme_key:
        return ""
    return f"{NRL_THEME_BASE}/{theme_key}/badge.svg"


# ---------- Primary: NRL.com ----------

def _fetch_from_nrl_com(year: int) -> dict | None:
    params = {"competition": NRL_COMP_ID, "season": year}
    try:
        r = requests.get(NRL_DRAW_URL, params=params, headers=HEADERS, timeout=20)
        print(f"[nrl] NRL.com {params} -> {r.status_code}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[nrl]   NRL.com fetch FAILED: {e}")
        return None


def _parse_nrl_com(data: dict) -> dict:
    fixtures: list[dict] = []
    round_label = ""

    for fix in data.get("fixtures") or []:
        round_label = fix.get("roundTitle") or round_label

        home_team = fix.get("homeTeam") or {}
        away_team = fix.get("awayTeam") or {}
        clock = fix.get("clock") or {}

        kickoff_iso = clock.get("kickOffTimeLong") or fix.get("startTime")
        if not kickoff_iso:
            continue
        try:
            normalized = kickoff_iso.replace("Z", "+00:00")
            dt_utc = datetime.fromisoformat(normalized)
        except Exception:
            continue
        dt_bne = dt_utc.astimezone(BRISBANE)

        state = fix.get("matchState") or "Upcoming"
        completed = state in COMPLETED_STATES
        live_label = LIVE_STATES.get(state)

        home_score = home_team.get("score")
        away_score = away_team.get("score")
        has_scores = home_score is not None and away_score is not None

        fixtures.append({
            "home": home_team.get("nickName") or "TBC",
            "away": away_team.get("nickName") or "TBC",
            "home_badge": _theme_badge((home_team.get("theme") or {}).get("key", "")),
            "away_badge": _theme_badge((away_team.get("theme") or {}).get("key", "")),
            "home_score": int(home_score) if completed and has_scores else (int(home_score) if has_scores and live_label else None),
            "away_score": int(away_score) if completed and has_scores else (int(away_score) if has_scores and live_label else None),
            "completed": completed,
            "live_label": live_label,  # "1st Half", "Half Time", "2nd Half" or None
            "day": dt_bne.strftime("%a %d %b"),
            "time": _format_time(dt_bne),
            "venue": fix.get("venue") or "",
            "datetime_iso": dt_bne.isoformat(),
        })

    fixtures.sort(key=lambda f: f["datetime_iso"])

    byes: list[str] = []
    for b in data.get("byes") or []:
        nick = b.get("teamNickName")
        if nick:
            byes.append(nick)

    print(f"[nrl] NRL.com: {round_label}, {len(fixtures)} fixtures, byes={byes}")
    return {"round_label": round_label, "fixtures": fixtures, "byes": byes}


# ---------- Fallback: static PDF JSON ----------

def _load_static(year: int) -> dict | None:
    for path in (
        ROOT / "config" / f"nrl_draw_{year}.json",
        ROOT / "config" / f"nrl_draw_{year - 1}.json",
    ):
        if path.exists():
            print(f"[nrl] static fallback: {path.name}")
            return json.loads(path.read_text())
    return None


def _parse_static_time(date_str: str, time_str: str):
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


def _find_current_round_static(static_data: dict, today_bne_date):
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


def _static_round_label(round_name: str) -> str:
    if not round_name:
        return ""
    s = round_name.strip().lower()
    if s.isdigit():
        return f"Round {int(s)}"
    n = WORD_TO_NUM.get(s)
    return f"Round {n}" if n else f"Round {round_name}"


def _parse_static_fallback(static_data: dict) -> dict:
    today_bne = datetime.now(BRISBANE).date()
    current = _find_current_round_static(static_data, today_bne)
    if not current:
        return {"round_label": "Off-Season", "fixtures": [], "byes": []}

    round_label = _static_round_label((current.get("round") or "").strip())
    byes = current.get("byes") or []

    fixtures: list[dict] = []
    for m in current.get("matches") or []:
        dt_bne = _parse_static_time(m.get("date", ""), (m.get("aedt_time") or "").strip())
        if not dt_bne:
            continue
        fixtures.append({
            "home": m.get("home") or "TBC",
            "away": m.get("away") or "TBC",
            "home_badge": _theme_badge(((m.get("home") or "").lower().replace(" ", "-"))),
            "away_badge": _theme_badge(((m.get("away") or "").lower().replace(" ", "-"))),
            "home_score": None,
            "away_score": None,
            "completed": False,
            "live_label": None,
            "day": dt_bne.strftime("%a %d %b"),
            "time": "TBC" if (m.get("aedt_time") or "").upper().strip() == "TBC" else _format_time(dt_bne),
            "venue": m.get("venue") or "",
            "datetime_iso": dt_bne.isoformat(),
        })

    fixtures.sort(key=lambda f: f["datetime_iso"])
    print(f"[nrl] static fallback: {round_label}, {len(fixtures)} fixtures, byes={byes}")
    return {"round_label": round_label, "fixtures": fixtures, "byes": byes}


# ---------- Public entrypoint ----------

def fetch_nrl_draw() -> dict:
    year = datetime.now(BRISBANE).year

    # Primary: NRL.com
    api_data = _fetch_from_nrl_com(year)
    if api_data and (api_data.get("fixtures") or api_data.get("byes")):
        return _parse_nrl_com(api_data)

    # Fallback: static PDF JSON
    static_data = _load_static(year)
    if static_data:
        return _parse_static_fallback(static_data)

    return {"round_label": "", "fixtures": [], "byes": []}
