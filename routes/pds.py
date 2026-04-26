import logging
import os

from flask import Blueprint, abort, current_app, g, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from extensions import limiter
from services.account_store import get_usage_count, increment_usage_count, is_paid
from services.event_log import log_event
from services.pds_generator import generate_pds


logger = logging.getLogger(__name__)
pds_bp = Blueprint("pds", __name__)

# Afstemming met services/pds_generator limieten
_MAX_POINTS = 8


@pds_bp.route("/generate", methods=["POST"])
@limiter.limit("10 per minute")
def generate():
    data = request.get_json(silent=True)

    if not data or "name" not in data:
        return jsonify({"success": False, "error": "Missing name"}), 400

    email = str(data.get("email", "")).strip().lower()
    if not email:
        return jsonify({"success": False, "error": "Missing email"}), 400

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"success": False, "error": "Invalid name"}), 400

    type_ = str(data.get("type", "offerte")).strip().lower()
    allowed_types = {"offerte", "technisch", "commercieel"}
    if type_ not in allowed_types:
        return jsonify({"success": False, "error": "Invalid type"}), 400

    goal = data.get("goal")
    if goal is not None and not isinstance(goal, str):
        return jsonify({"success": False, "error": "Invalid goal"}), 400
    goal = (goal or "").strip()

    summary = data.get("summary")
    if summary is not None and not isinstance(summary, str):
        return jsonify({"success": False, "error": "Invalid summary"}), 400
    summary = (summary or "").strip()

    document_date = data.get("document_date")
    if document_date is not None and not isinstance(document_date, str):
        return jsonify({"success": False, "error": "Invalid document_date"}), 400
    document_date = (document_date or "").strip()

    client = data.get("client")
    if client is not None and not isinstance(client, str):
        return jsonify({"success": False, "error": "Invalid client"}), 400
    client = (client or "").strip()

    points = data.get("points")
    if points is not None and not isinstance(points, list):
        return jsonify({"success": False, "error": "Invalid points (expected array of strings)"}), 400
    if points is None:
        points = []
    if len(points) > _MAX_POINTS:
        return jsonify({"success": False, "error": f"At most {_MAX_POINTS} points allowed"}), 400
    for p in points:
        if not isinstance(p, str):
            return jsonify({"success": False, "error": "Each point must be a string"}), 400

    free_limit = int(current_app.config.get("FREE_GENERATION_LIMIT", 3))
    paid_user = is_paid(email)
    usage_count = get_usage_count(email)
    if not paid_user and usage_count >= free_limit:
        log_event(
            "pds.generate.blocked",
            request_id=g.get("request_id"),
            email=email,
            payload={"reason": "free_limit", "usage": usage_count, "limit": free_limit},
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Gratis limiet bereikt. Upgrade nodig.",
                    "upgrade_required": True,
                }
            ),
            403,
        )

    try:
        result = generate_pds(
            {
                "name": name,
                "type": type_,
                "goal": goal,
                "summary": summary,
                "document_date": document_date,
                "client": client,
                "points": points,
            },
            current_app.config["PDS_OUTPUT_DIR"],
        )
    except Exception:
        log_event(
            "pds.generate.error",
            request_id=g.get("request_id"),
            email=email,
            payload={"type": type_},
        )
        logger.exception("[%s] PDF generation failed", g.get("request_id", "-"))
        return jsonify({"success": False, "error": "Failed to generate PDF"}), 500

    if not paid_user:
        usage_count = increment_usage_count(email)

    _ok_p = {
        "type": type_,
        "artifact": result.get("filename"),
        "is_paid": bool(paid_user),
    }
    if not paid_user:
        _ok_p["usage_count"] = int(usage_count)
    log_event(
        "pds.generate.ok",
        request_id=g.get("request_id"),
        email=email,
        payload=_ok_p,
    )
    logger.info("[%s] Generated: %s", g.get("request_id", "-"), result["filename"])
    return jsonify(
        {
            "success": True,
            "data": result,
            "meta": {
                "is_paid": paid_user,
                "usage_count": usage_count,
                "free_limit": free_limit,
            },
        }
    )


@pds_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    safe_name = secure_filename(filename)

    if not safe_name or safe_name != filename:
        abort(400, description="Invalid filename")

    if not safe_name.lower().endswith(".pdf"):
        abort(400, description="Invalid file type")

    base_dir = current_app.config["PDS_OUTPUT_DIR"]
    file_path = os.path.join(base_dir, safe_name)
    if not os.path.isfile(file_path):
        abort(404, description="File not found")

    log_event(
        "pds.download",
        request_id=g.get("request_id"),
        payload={"artifact": safe_name},
    )
    logger.info("[%s] Download: %s", g.get("request_id", "-"), safe_name)
    return send_from_directory(
        base_dir,
        safe_name,
        as_attachment=True,
        mimetype="application/pdf",
        max_age=0,
    )
