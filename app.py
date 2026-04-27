import logging
import os
import uuid

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from extensions import limiter
from routes.admin import admin_bp
from routes.billing import billing_bp
from routes.leads import leads_bp
from routes.pds import pds_bp


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    env = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).lower()
    if env == "production":
        app.config.from_object("config.ProductionConfig")
    else:
        app.config.from_object("config.DevelopmentConfig")

    _sk = (app.config.get("SECRET_KEY") or "").strip()
    if env == "production" and not _sk:
        raise RuntimeError(
            "SECRET_KEY must be set in production (e.g. Render Environment Variables)."
        )

    if env == "production":
        # Achter Nginx, Cloudflare, Render, enz.: X-Forwarded-* respecteren
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    CORS(
        app,
        resources={
            r"/pds/*": {"origins": app.config["CORS_ORIGINS"]},
            r"/billing/*": {"origins": app.config["CORS_ORIGINS"]},
            r"/leads/*": {"origins": app.config["CORS_ORIGINS"]},
            r"/admin/*": {"origins": app.config["CORS_ORIGINS"]},
        },
        supports_credentials=False,
    )

    limiter.init_app(app)
    app.register_blueprint(pds_bp, url_prefix="/pds")
    app.register_blueprint(billing_bp, url_prefix="/billing")
    app.register_blueprint(leads_bp, url_prefix="/leads")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.before_request
    def add_request_id():
        g.request_id = uuid.uuid4().hex[:8]
        logger.info("[%s] %s %s", g.request_id, request.method, request.path)

    @app.after_request
    def attach_request_id(response):
        response.headers["X-Request-ID"] = g.get("request_id", "-")
        return response

    @app.errorhandler(400)
    def bad_request(error):
        return (
            jsonify(
                {
                    "success": False,
                    "error": getattr(error, "description", "Bad request"),
                }
            ),
            400,
        )

    @app.errorhandler(404)
    def not_found(error):
        return (
            jsonify({"success": False, "error": getattr(error, "description", "Not found")}),
            404,
        )

    @app.errorhandler(429)
    def rate_limited(error):
        return (
            jsonify({"success": False, "error": "Too many requests"}),
            429,
        )

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"success": False, "error": "Internal server error"}), 500

    @limiter.exempt
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/", methods=["GET"])
    def root():
        return jsonify(
            {
                "service": "jmcovenant-backend",
                "status": "ok",
                "health": "/health",
            }
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )
