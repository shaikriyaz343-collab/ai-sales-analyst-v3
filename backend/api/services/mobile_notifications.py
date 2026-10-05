from __future__ import annotations

import json
from urllib import request as urlrequest


def send_mobile_alert_notifications(tokens: list[str], *, title: str, body: str, data: dict[str, object] | None = None) -> int:
    """Send a bounded batch of Expo push notifications and return successful ticket count."""
    clean = []
    for token in tokens:
        token = str(token).strip()
        if token.startswith("ExponentPushToken[") and token.endswith("]"):
            clean.append(token)
    if not clean:
        return 0
    messages = [
        {
            "to": token,
            "sound": "default",
            "title": title,
            "body": body,
            "data": data or {},
        }
        for token in clean[:100]
    ]
    payload = json.dumps(messages, separators=(",", ":")).encode("utf-8")
    req = urlrequest.Request(
        "https://exp.host/--/api/v2/push/send",
        data=payload,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-encoding": "gzip, deflate",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=10) as response:
            if response.status != 200:
                return 0
            result = json.loads(response.read().decode("utf-8"))
    except Exception:
        return 0
    tickets = result.get("data", []) if isinstance(result, dict) else []
    return sum(1 for ticket in tickets if isinstance(ticket, dict) and ticket.get("status") == "ok")
