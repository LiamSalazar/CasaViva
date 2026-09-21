import os
import tempfile
from pathlib import Path

from .test import *  # noqa: F403

DEBUG = True
# ``base`` derives this value while its production-safe DEBUG=False default is
# still in effect.  Re-evaluate it after enabling the dedicated test settings.
TURNSTILE_TEST_TOKEN = os.environ.get("TURNSTILE_TEST_TOKEN", "")
if os.environ.get("CASAVIVA_E2E") == "1":
    REST_FRAMEWORK = {
        **REST_FRAMEWORK,  # noqa: F405
        "DEFAULT_THROTTLE_RATES": {
            **REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],  # noqa: F405
            "login": "60/min",
            "mfa": "60/min",
            "inquiry": "60/hour",
            # Playwright exercises the full public navigation flow from one
            # loopback address.  Keep production limits intact while ensuring
            # that a complete isolated suite cannot exhaust the shared anon
            # bucket midway through its deterministic fixture checks.
            "anon": "1000/min",
            "search": "1000/min",
            "analytics": "1000/min",
        },
    }
database_name = os.environ.get("POSTGRES_TEST_DB", "casaviva_test")
if "test" not in database_name.lower():
    raise RuntimeError("POSTGRES_TEST_DB debe contener 'test'; se rechazó una base potencialmente real.")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_name,
        "USER": os.environ.get("POSTGRES_TEST_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_TEST_PASSWORD", "casaviva-postgres-test"),
        "HOST": os.environ.get("POSTGRES_TEST_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_TEST_PORT", "55432"),
        "CONN_MAX_AGE": 0,
        "TEST": {"NAME": f"{database_name}_pytest"},
    }
}
MEDIA_ROOT = Path(tempfile.gettempdir()) / "casaviva-postgres-test-media"
