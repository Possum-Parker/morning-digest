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

    # Try several segment names — OneSignal renamed defaults across versions, and
    # some accounts only have one of these. We stop at the first successful send.
    segment_candidates = ["Total Subscriptions", "Subscribed Users", "Active Subscriptions"]

    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }
    last_response = None

    for segment in segment_candidates:
        payload = {
            "app_id": app_id,
            "target_channel": "push",
            "included_segments": [segment],
            "headings": {"en": "Morning Digest ready"},
            "contents": {"en": headline[:180]},
            "url": os.environ.get("PWA_URL", ""),
        }
        resp = requests.post(ONESIGNAL_API, headers=headers, json=payload, timeout=20)
        body_preview = resp.text[:240]
        print(f"[push] segment='{segment}' status={resp.status_code} body={body_preview}")

        last_response = resp
        if not resp.ok:
            continue

        body = resp.json() if resp.text else {}
        # OneSignal returns 200 even when delivery is rejected — only treat as success
        # if we got a notification id back AND there are no errors.
        if body.get("errors"):
            continue
        if body.get("id"):
            return body

    return last_response.json() if (last_response and last_response.text) else None
