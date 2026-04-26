import os

_BASE_CORS = [
    "https://jmcovenant.nl",
    "https://www.jmcovenant.nl",
    "https://staging.jmcovenant.nl",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def _merge_cors_extra(base):
    extra = os.getenv("CORS_EXTRA_ORIGINS", "")
    if not extra.strip():
        return list(base)
    out = list(base)
    for item in extra.split(","):
        origin = item.strip()
        if origin and origin not in out:
            out.append(origin)
    return out


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB
    JSONIFY_PRETTYPRINT_REGULAR = False
    PROPAGATE_EXCEPTIONS = False
    FREE_GENERATION_LIMIT = int(os.getenv("FREE_GENERATION_LIMIT", "3"))
    PDS_OUTPUT_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "generated_pds")
    )
    CORS_ORIGINS = _merge_cors_extra(_BASE_CORS)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
