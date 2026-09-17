#!/usr/bin/env python3
"""Render SSM Parameter Store JSON as a safe Compose dotenv file."""

import argparse
import json
import sys
from urllib.parse import quote


def dotenv(value: str) -> str:
    if "\0" in value or "\n" in value or "\r" in value:
        raise ValueError("dotenv values cannot contain NUL or newlines")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
    return f'"{escaped}"'


def database_url(user: str, password: str, host: str, port: str, name: str) -> str:
    return f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}/{quote(name, safe='')}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images-sha", required=True)
    parser.add_argument("--registry", required=True)
    args = parser.parse_args()
    payload = json.load(sys.stdin)
    values = {item["Name"].rsplit("/", 1)[-1]: item["Value"] for item in payload["Parameters"]}
    required = {
        "POSTGRES_SUPERUSER_PASSWORD", "APP_DATABASE_PASSWORD", "MIGRATOR_DATABASE_PASSWORD",
        "BACKUP_DATABASE_PASSWORD", "READONLY_DATABASE_PASSWORD",
    }
    missing = sorted(required - values.keys())
    if missing:
        raise SystemExit("Missing required SSM parameters: " + ", ".join(missing))
    host = values.get("DATABASE_HOST", "postgres")
    port = values.get("DATABASE_PORT", "5432")
    name = values.get("POSTGRES_DB", "casaviva")
    app_password = values.pop("APP_DATABASE_PASSWORD")
    migrator_password = values.pop("MIGRATOR_DATABASE_PASSWORD")
    backup_password = values.pop("BACKUP_DATABASE_PASSWORD")
    readonly_password = values.pop("READONLY_DATABASE_PASSWORD")
    values["APP_DATABASE_URL"] = database_url("casaviva_app", app_password, host, port, name)
    values["MIGRATOR_DATABASE_URL"] = database_url("casaviva_migrator", migrator_password, host, port, name)
    values["BACKUP_DATABASE_URL"] = database_url("casaviva_backup", backup_password, host, port, name)
    values["CASAVIVA_APP_PASSWORD"] = app_password
    values["CASAVIVA_MIGRATOR_PASSWORD"] = migrator_password
    values["CASAVIVA_BACKUP_PASSWORD"] = backup_password
    values["CASAVIVA_READONLY_PASSWORD"] = readonly_password
    values["FRONTEND_IMAGE"] = f"{args.registry}/casaviva-frontend:{args.images_sha}"
    values["BACKEND_IMAGE"] = f"{args.registry}/casaviva-backend:{args.images_sha}"
    for key in sorted(values):
        if not key.replace("_", "").isalnum() or not key[0].isalpha():
            raise SystemExit(f"Invalid environment name: {key}")
        print(f"{key}={dotenv(str(values[key]))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
