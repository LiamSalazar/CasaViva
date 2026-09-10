from .base import *  # noqa: F403

if SECRET_KEY == "unsafe-development-only":  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY is required in production")
if not ALLOWED_HOSTS:  # noqa: F405
    raise RuntimeError("ALLOWED_HOSTS must be explicit in production")
if not os.environ.get("DATABASE_URL"):  # noqa: F405
    raise RuntimeError("DATABASE_URL is required in production")
if STORAGE_BACKEND not in {"local", "s3"}:  # noqa: F405
    raise RuntimeError("STORAGE_BACKEND must be local or s3")
if STORAGE_BACKEND == "s3":  # noqa: F405
    required_storage = ["S3_BUCKET_NAME"]
    missing_storage = [name for name in required_storage if not os.environ.get(name)]
    if missing_storage:
        raise RuntimeError(f"Missing S3 storage settings: {', '.join(missing_storage)}")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "false").lower() == "true"
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "false").lower() == "true"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
