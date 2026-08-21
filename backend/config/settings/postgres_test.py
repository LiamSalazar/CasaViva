import os
import tempfile
from pathlib import Path

from .test import *  # noqa: F403

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
