import csv
import os
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from extensions import limiter


leads_bp = Blueprint("leads", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
FILE_PATH = os.path.join(BASE_DIR, "leads.csv")


def _normalize_email(value):
    return str(value or "").strip().lower()


@leads_bp.route("/waitlist", methods=["POST"])
@limiter.limit("5 per minute")
def waitlist():
    data = request.get_json(silent=True) or {}
    email = _normalize_email(data.get("email"))
    if not email:
        return jsonify({"success": False, "error": "Email vereist"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"success": False, "error": "Ongeldig emailadres"}), 400

    os.makedirs(BASE_DIR, exist_ok=True)
    file_exists = os.path.isfile(FILE_PATH)

    if file_exists:
        with open(FILE_PATH, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if _normalize_email(row.get("email")) == email:
                    return jsonify({"success": True, "message": "Al aangemeld"})

    with open(FILE_PATH, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if not file_exists:
            writer.writerow(["email", "date"])
        writer.writerow([email, datetime.now(timezone.utc).isoformat()])

    return jsonify({"success": True})
