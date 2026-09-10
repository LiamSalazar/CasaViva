from pathlib import Path
import os
from urllib.parse import urlparse, unquote
from django.utils.csp import CSP
from config.env import load_project_environment

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parent
load_project_environment()

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-development-only")
DEBUG = False
ALLOWED_HOSTS = [x.strip() for x in os.environ.get("ALLOWED_HOSTS", "").split(",") if x.strip()]

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]
ENABLE_TECHNICAL_ADMIN = os.environ.get("ENABLE_TECHNICAL_ADMIN", "false").lower() == "true"
if ENABLE_TECHNICAL_ADMIN:
    DJANGO_APPS.append("django.contrib.admin")
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local").lower()
if STORAGE_BACKEND == "s3":
    DJANGO_APPS.append("storages")
THIRD_PARTY_APPS = ["rest_framework", "django_filters", "django_otp", "django_otp.plugins.otp_totp", "drf_spectacular"]
LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.geo",
    "apps.media_library",
    "apps.catalog",
    "apps.listings",
    "apps.crm",
    "apps.analytics",
    "apps.audit",
    "apps.content",
    "apps.marketing",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.RequestIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.common.middleware.ApiTrailingSlashMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.AuthorizationVersionMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "casaviva"),
        "USER": os.environ.get("POSTGRES_USER", "casaviva_app"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}
if os.environ.get("DATABASE_URL"):
    parsed = urlparse(os.environ["DATABASE_URL"])
    DATABASES["default"].update({
        "NAME": unquote(parsed.path.lstrip("/")), "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""), "HOST": parsed.hostname or "", "PORT": str(parsed.port or 5432),
    })
if os.environ.get("DB_SSL_REQUIRE", "false").lower() == "true":
    DATABASES["default"]["OPTIONS"] = {"sslmode": "require"}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
CASAVIVA_MODE = os.environ.get("CASAVIVA_MODE", "normal").lower()
PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "http://localhost:3000")
if CASAVIVA_MODE == "demo":
    MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media_demo"))
if STORAGE_BACKEND == "s3":
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    # Empty values let boto3 use the AWS credential provider chain (EC2 role).
    AWS_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID") or None
    AWS_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY") or None
    AWS_STORAGE_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL") or None
    AWS_S3_REGION_NAME = os.environ.get("S3_REGION") or None
    AWS_S3_CUSTOM_DOMAIN = os.environ.get("S3_CUSTOM_DOMAIN") or None
    AWS_QUERYSTRING_AUTH = os.environ.get("S3_QUERYSTRING_AUTH", "true").lower() == "true"
    AWS_QUERYSTRING_EXPIRE = int(os.environ.get("S3_QUERYSTRING_EXPIRE", "3600"))
    AWS_DEFAULT_ACL = None
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]
SESSION_COOKIE_AGE = 60 * 60 * 8
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:"],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "script-src": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.CasaVivaPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend", "rest_framework.filters.OrderingFilter", "rest_framework.filters.SearchFilter"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle", "rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "120/min", "user": "600/min", "login": "8/min", "mfa": "8/min", "inquiry": "10/hour", "analytics": "300/min", "search": "120/min"},
}
SPECTACULAR_SETTINGS = {"TITLE": "CasaViva API", "VERSION": "1.0.0", "SERVE_INCLUDE_SCHEMA": False}

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", 10 * 1024 * 1024))
ANTIBOT_ENABLED = os.environ.get("ANTIBOT_ENABLED", "false").lower() == "true"
ANTIBOT_PROVIDER = os.environ.get("ANTIBOT_PROVIDER", "turnstile")
TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "")
LEAD_NOTIFICATION_BACKEND = os.environ.get("LEAD_NOTIFICATION_BACKEND", "django_email")
LEAD_NOTIFICATION_EMAIL = os.environ.get("LEAD_NOTIFICATION_EMAIL", "")
ANALYTICS_RETENTION_DAYS = int(os.environ["ANALYTICS_RETENTION_DAYS"]) if os.environ.get("ANALYTICS_RETENTION_DAYS") else None
INACTIVE_LEAD_RETENTION_DAYS = int(os.environ["INACTIVE_LEAD_RETENTION_DAYS"]) if os.environ.get("INACTIVE_LEAD_RETENTION_DAYS") else None

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "apps.common.logging.JsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
