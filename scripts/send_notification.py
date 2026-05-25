"""Send a push notification via OneSignal REST API."""
from __future__ import annotations

import os

import requests


ONESIGNAL_API = "https://api.onesignal.com/notifications"


def send_push(headline: str) -> dict | None:
    app_id = os.environ.get("ONESIGNAL_APP_ID")
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY")
    if not app_id or not api_key:
        print("[push] OneSignal credentials not set — skipping push notification.")
        return None

    payload = {
        "app_id": app_id,
        "included_segments": ["Subscribed Users"],
        "headings": {"en": "Morning Digest ready"},
        "contents": {"en": headline[:180]},
        "url": os.environ.get("PWA_URL", ""),
    }

    resp = requests.post(
        ONESIGNAL_API,
        headers={
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )
    print(f"[push] OneSignal status={resp.status_code} body={resp.text[:200]}")
    return resp.json() if resp.ok else None
