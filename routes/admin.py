import csv
import hmac
import os

from flask import Blueprint, jsonify, render_template, request

from extensions import limiter
from services.account_store import get_all_accounts


admin_bp = Blueprint("admin", __name__)


def _require_admin_api_key():
    provided = request.headers.get("X-Api-Key", "")
    expected = os.getenv("INTERNAL_API_KEY", "")
    if not expected or not hmac.compare_digest(provided, expected):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return None


@admin_bp.route("/dashboard", methods=["GET"])
def dashboard():
    return render_template("admin_dashboard.html")


@admin_bp.route("/stats", methods=["GET"])
@limiter.limit("30 per minute")
def get_stats():
    unauthorized = _require_admin_api_key()
    if unauthorized:
        return unauthorized

    accounts = get_all_accounts()
    total_users = len(accounts)
    paid_users = sum(1 for account in accounts if account["is_paid"])
    free_users = total_users - paid_users
    total_usage = sum(account["usage_count"] for account in accounts)
    avg_usage = (total_usage / total_users) if total_users else 0

    return jsonify(
        {
            "success": True,
            "total_users": total_users,
            "paid_users": paid_users,
            "free_users": free_users,
            "total_usage": total_usage,
            "avg_usage": round(avg_usage, 2),
        }
    )


@admin_bp.route("/users", methods=["GET"])
@limiter.limit("30 per minute")
def get_users():
    unauthorized = _require_admin_api_key()
    if unauthorized:
        return unauthorized

    accounts = get_all_accounts()
    users = sorted(accounts, key=lambda account: account["usage_count"], reverse=True)
    return jsonify({"success": True, "users": users})


@admin_bp.route("/leads", methods=["GET"])
@limiter.limit("30 per minute")
def get_leads():
    unauthorized = _require_admin_api_key()
    if unauthorized:
        return unauthorized

    leads_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "leads.csv")
    )
    if not os.path.isfile(leads_file):
        return jsonify({"success": True, "leads": []})

    leads = []
    with open(leads_file, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            leads.append(row)

    return jsonify({"success": True, "leads": leads[::-1]})
