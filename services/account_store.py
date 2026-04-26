import csv
import os
from datetime import datetime, timezone


DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
USERS_FILE = os.path.join(DATA_DIR, "users.csv")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _normalize_email(email):
    return str(email or "").strip().lower()


def _ensure_users_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.isfile(USERS_FILE):
        return
    with open(USERS_FILE, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["email", "is_paid", "usage_count", "updated_at"]
        )
        writer.writeheader()


def _load_users():
    _ensure_users_file()
    users = {}
    with open(USERS_FILE, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            email = _normalize_email(row.get("email"))
            if not email:
                continue
            usage_count = row.get("usage_count", "0")
            users[email] = {
                "email": email,
                "is_paid": "1" if row.get("is_paid") == "1" else "0",
                "usage_count": str(int(usage_count) if str(usage_count).isdigit() else 0),
                "updated_at": row.get("updated_at") or _now_iso(),
            }
    return users


def _save_users(users):
    _ensure_users_file()
    temp_file = f"{USERS_FILE}.tmp"
    with open(temp_file, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["email", "is_paid", "usage_count", "updated_at"]
        )
        writer.writeheader()
        for email in sorted(users):
            writer.writerow(users[email])
    os.replace(temp_file, USERS_FILE)


def ensure_user(email):
    normalized = _normalize_email(email)
    if not normalized:
        return None
    users = _load_users()
    if normalized not in users:
        users[normalized] = {
            "email": normalized,
            "is_paid": "0",
            "usage_count": "0",
            "updated_at": _now_iso(),
        }
        _save_users(users)
    return normalized


def is_paid(email):
    normalized = _normalize_email(email)
    if not normalized:
        return False
    users = _load_users()
    return users.get(normalized, {}).get("is_paid") == "1"


def set_paid(email, paid):
    normalized = ensure_user(email)
    if not normalized:
        return
    users = _load_users()
    users[normalized]["is_paid"] = "1" if paid else "0"
    users[normalized]["updated_at"] = _now_iso()
    _save_users(users)


def get_usage_count(email):
    normalized = _normalize_email(email)
    if not normalized:
        return 0
    users = _load_users()
    usage = users.get(normalized, {}).get("usage_count", "0")
    return int(usage) if str(usage).isdigit() else 0


def increment_usage_count(email):
    normalized = ensure_user(email)
    if not normalized:
        return 0
    users = _load_users()
    current = int(users[normalized].get("usage_count", "0"))
    users[normalized]["usage_count"] = str(current + 1)
    users[normalized]["updated_at"] = _now_iso()
    _save_users(users)
    return current + 1


def get_all_accounts():
    users = _load_users()
    accounts = []
    for email in sorted(users):
        row = users[email]
        usage = row.get("usage_count", "0")
        usage_count = int(usage) if str(usage).isdigit() else 0
        accounts.append(
            {
                "email": email,
                "is_paid": row.get("is_paid") == "1",
                "usage_count": usage_count,
                "updated_at": row.get("updated_at") or _now_iso(),
            }
        )
    return accounts
