import os
import subprocess
import sys

from config.env import load_project_environment


def test_test_settings_trust_only_explicit_local_frontend_origins(settings):
    assert settings.CSRF_TRUSTED_ORIGINS == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_dotenv_loads_value(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("CASAVIVA_ENV_TEST=desde-archivo\n", encoding="utf-8")
    monkeypatch.delenv("CASAVIVA_ENV_TEST", raising=False)
    load_project_environment(env_file)
    assert os.environ["CASAVIVA_ENV_TEST"] == "desde-archivo"


def test_process_environment_has_priority_over_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("CASAVIVA_ENV_TEST=desde-archivo\n", encoding="utf-8")
    monkeypatch.setenv("CASAVIVA_ENV_TEST", "desde-proceso")
    load_project_environment(env_file)
    assert os.environ["CASAVIVA_ENV_TEST"] == "desde-proceso"


def test_missing_dotenv_does_not_fail(tmp_path, monkeypatch):
    monkeypatch.delenv("CASAVIVA_ENV_TEST", raising=False)
    selected = load_project_environment(tmp_path / "no-existe.env")
    assert selected.name == "no-existe.env"


def test_production_without_secret_key_fails_explicitly(tmp_path):
    environment = os.environ.copy()
    environment.pop("DJANGO_SECRET_KEY", None)
    environment.update({
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "CASAVIVA_ENV_FILE": str(tmp_path / "no-existe.env"),
        "ALLOWED_HOSTS": "example.test",
    })
    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]),
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY is required in production" in result.stderr
