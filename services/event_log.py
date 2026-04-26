"""
Minimale, future-proof eventregel: append-only JSONL.

- Bestand: default `data/events.jsonl` (tuning via EVENT_LOG_PATH).
- Richting: later eenvoudig vervangen of dupliceren naar DB / ELK (zelfde JSON per regel).
- Schema: v=1, ts (UTC ISO), event (namespaced), req (request_id), actor (HMAC, geen PII in log),
  payload (alleen primitieven; geen Stripe-rouwe objecten).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Optional

_lock = threading.Lock()
_SCHEMA = 1

# Event-namen: domein.aktie[.resultaat] — uitbreidbaar zonder migratie
# Voorbeelden: pds.generate.ok, billing.stripe.subscription_updated


def _data_dir():
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data")
    )


def _log_path():
    p = os.getenv("EVENT_LOG_PATH", "").strip()
    if p:
        return os.path.abspath(p)
    return os.path.join(_data_dir(), "events.jsonl")


def _enabled():
    return os.getenv("EVENT_LOG_ENABLED", "1").lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _actor_ref(email: str) -> Optional[str]:
    if not (email or "").strip():
        return None
    email = str(email).strip().lower()
    if os.getenv("EVENT_LOG_PLAIN_EMAIL", "0").lower() in (
        "1",
        "true",
        "yes",
    ):
        return email
    sk = (os.getenv("SECRET_KEY") or os.getenv("EVENT_LOG_HMAC_SALT", "")).encode()
    if not sk:
        sk = b"__set_secret_key_for_stable_actor_h__"
    return hmac.new(sk, email.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def log_event(
    event: str,
    *,
    request_id: Optional[str] = None,
    email: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
):
    if not _enabled():
        return
    row = {
        "v": _SCHEMA,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": str(event)[:200],
        "req": (request_id or "")[:32] or None,
        "actor": _actor_ref(email) if email else None,
        "payload": _sanitize_payload(payload or {}),
    }
    for k in list(row):
        if row[k] is None:
            del row[k]
    line = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
    path = _log_path()
    with _lock:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line)


def _sanitize_payload(data: dict) -> dict:
    out = {}
    for key, value in data.items():
        k = str(key)[:80]
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[k] = _truncate_value(value)
        elif isinstance(value, (list, tuple)) and len(value) <= 24:
            out[k] = [_truncate_value(x) for x in value[:24] if isinstance(x, (str, int, float, bool))]
    return out


def _truncate_value(value, max_str=2000, max_int=1 << 62):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value) if abs(int(value)) < max_int else 0
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        s = value.replace("\n", " ").replace("\r", " ")
        return s if len(s) <= max_str else s[: max_str - 3] + "..."
    return str(value)[:200]
