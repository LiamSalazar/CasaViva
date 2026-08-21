import os
from pathlib import Path

from dotenv import load_dotenv


def load_project_environment(env_path=None):
    """Load the repository .env without replacing process-level settings."""
    default_path = Path(__file__).resolve().parents[2] / ".env"
    selected = Path(env_path or os.environ.get("CASAVIVA_ENV_FILE", default_path))
    load_dotenv(selected, override=False)
    return selected
