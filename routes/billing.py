import hmac
import logging
import os
import re

import stripe
from flask import Blueprint, g, jsonify, request

from extensions import limiter
from services.account_store import get_usage_count, is_paid, set_paid
from services.event_log import log_event


logger = logging.getLogger(__name__)
billing_bp = Blueprint("billing", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value):
    return str(value or "").strip().lower()


def _validate_email(email):
    return bool(EMAIL_RE.match(email))


def _require_status_api_key():
    provided = request.headers.get("X-Api-Key", "")
    expected = os.getenv("INTERNAL_API_KEY", "")
    if not expected or not hmac.compare_digest(provided, expected):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return None


def _email_from_subscription(subscription):
    """Stripe Subscription bevat niet altijd metadata; fallback via Customer."""
    meta = (subscription.get("metadata") or {}) if isinstance(subscription, dict) else {}
    email = _normalize_email(meta.get("email"))
    if email:
        return email
    cust_id = subscription.get("customer")
    if not cust_id:
        return None
    try:
        cust = stripe.Customer.retrieve(cust_id)
        return _normalize_email(cust.get("email"))
    except Exception:
        logger.exception("Could not resolve email from subscription customer %s", cust_id)
    return None


@billing_bp.route("/create-checkout-session", methods=["POST"])
@limiter.limit("10 per minute")
def create_checkout():
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    price_id = os.getenv("STRIPE_PRICE_ID", "")
    frontend_url = os.getenv("FRONTEND_BASE_URL", "https://jmcovenant.nl")

    if not stripe.api_key or not price_id:
        logger.error("Stripe is not configured correctly")
        return jsonify({"success": False, "error": "Billing is not configured"}), 500

    data = request.get_json(silent=True) or {}
    email = _normalize_email(data.get("email"))
    if not email:
        return jsonify({"success": False, "error": "Email vereist"}), 400
    if not _validate_email(email):
        return jsonify({"success": False, "error": "Ongeldig emailadres"}), 400

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=email,
            line_items=[{"price": price_id, "quantity": 1}],
            metadata={"email": email},
            subscription_data={"metadata": {"email": email}},
            success_url=f"{frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/cancel",
        )
    except Exception:
        logger.exception("Stripe checkout session creation failed")
        return jsonify({"success": False, "error": "Checkout creation failed"}), 500

    return jsonify({"success": True, "url": session.url})


@billing_bp.route("/webhook", methods=["POST"])
@limiter.exempt
def webhook():
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    signature = request.headers.get("Stripe-Signature", "")

    if not stripe.api_key or not endpoint_secret:
        return jsonify({"success": False, "error": "Webhook not configured"}), 500

    try:
        event = stripe.Webhook.construct_event(request.data, signature, endpoint_secret)
    except Exception:
        return jsonify({"success": False, "error": "Invalid webhook"}), 400

    event_type = event.get("type", "")
    payload = event.get("data", {}).get("object", {})

    req_id = g.get("request_id")
    if event_type == "checkout.session.completed":
        email = _normalize_email(
            payload.get("customer_email") or (payload.get("metadata") or {}).get("email")
        )
        if email:
            set_paid(email, True)
        log_event(
            "billing.stripe.checkout_done",
            request_id=req_id,
            email=email,
            payload={"stripe_event": event_type, "paid": True if email else False},
        )

    elif event_type == "customer.subscription.deleted":
        email = _email_from_subscription(payload)
        if email:
            set_paid(email, False)
        log_event(
            "billing.stripe.subscription_ended",
            request_id=req_id,
            email=email,
            payload={"stripe_event": event_type, "paid": False if email else None},
        )

    elif event_type == "customer.subscription.updated":
        email = _email_from_subscription(payload)
        if not email:
            return jsonify({"success": True})
        status = (payload.get("status") or "").lower()
        paid_next = None
        # actief of proef: toegang; beëindigd: uit (past_due = grace: toegang laten staan)
        if status in ("active", "trialing"):
            set_paid(email, True)
            paid_next = True
        elif status in {"canceled", "unpaid", "incomplete_expired", "incomplete", "ended"}:
            set_paid(email, False)
            paid_next = False
        log_event(
            "billing.stripe.subscription_updated",
            request_id=req_id,
            email=email,
            payload={
                "stripe_event": event_type,
                "sub_status": status,
                "access": paid_next,
            },
        )

    return jsonify({"success": True})


@billing_bp.route("/status", methods=["POST"])
@limiter.limit("60 per minute")
def status():
    unauthorized = _require_status_api_key()
    if unauthorized:
        return unauthorized

    data = request.get_json(silent=True) or {}
    email = _normalize_email(data.get("email"))
    if not email:
        return jsonify({"success": False, "error": "Email vereist"}), 400
    if not _validate_email(email):
        return jsonify({"success": False, "error": "Ongeldig emailadres"}), 400

    return jsonify(
        {
            "success": True,
            "is_paid": is_paid(email),
            "usage_count": get_usage_count(email),
        }
    )
