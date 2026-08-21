import os
import subprocess
import uuid
from pathlib import Path

import psycopg
import pytest
from django.db import connection


pytestmark = pytest.mark.postgres


def role_connection(role, password):
    return psycopg.connect(
        host=os.environ.get("POSTGRES_TEST_HOST", "127.0.0.1"),
        port=os.environ.get("POSTGRES_TEST_PORT", "55432"),
        dbname=os.environ.get("POSTGRES_TEST_DB", "casaviva_test"),
        user=role,
        password=password,
        autocommit=True,
    )


@pytest.fixture(autouse=True)
def require_postgres():
    if connection.vendor != "postgresql":
        pytest.skip("La matriz de roles requiere PostgreSQL real.")
    if "test" not in os.environ.get("POSTGRES_TEST_DB", "casaviva_test").lower():
        pytest.fail("La prueba de roles rechazó una base cuyo nombre no contiene test.")


def test_audit_is_insertable_and_readable_but_immutable_for_app_role():
    event_id = uuid.uuid4()
    with role_connection("casaviva_app", "casaviva-app-test") as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO audit_auditevent (id, occurred_at, action, entity_type, entity_id, success) VALUES (%s, now(), 'CREATE', 'RoleTest', %s, true)",
                [event_id, str(event_id)],
            )
            cursor.execute("SELECT action FROM audit_auditevent WHERE id = %s", [event_id])
            assert cursor.fetchone() == ("CREATE",)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute("UPDATE audit_auditevent SET action = 'UPDATE' WHERE id = %s", [event_id])
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute("DELETE FROM audit_auditevent WHERE id = %s", [event_id])


@pytest.mark.parametrize(
    ("role", "password"),
    [("casaviva_readonly", "casaviva-readonly-test"), ("casaviva_backup", "casaviva-backup-test")],
)
def test_read_roles_can_select_but_cannot_write(role, password):
    with role_connection(role, password) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM django_migrations")
            assert cursor.fetchone()[0] > 0
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute(
                    "INSERT INTO django_session (session_key, session_data, expire_date) VALUES (%s, '', now())",
                    [uuid.uuid4().hex],
                )
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute("UPDATE django_migrations SET name = name")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute("DELETE FROM django_migrations WHERE false")


def test_app_role_has_crud_but_no_cluster_administration():
    session_key = uuid.uuid4().hex
    with role_connection("casaviva_app", "casaviva-app-test") as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user")
            assert cursor.fetchone() == (False, False, False)
            cursor.execute("INSERT INTO django_session (session_key, session_data, expire_date) VALUES (%s, 'x', now() + interval '1 hour')", [session_key])
            cursor.execute("UPDATE django_session SET session_data = 'y' WHERE session_key = %s", [session_key])
            cursor.execute("SELECT session_data FROM django_session WHERE session_key = %s", [session_key])
            assert cursor.fetchone() == ("y",)
            cursor.execute("DELETE FROM django_session WHERE session_key = %s", [session_key])
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute("CREATE ROLE forbidden_role")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute("CREATE DATABASE forbidden_database")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute("ALTER ROLE casaviva_app CREATEDB")


def test_backup_role_can_complete_logical_backup():
    repository = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "docker", "compose", "-f", str(repository / "docker-compose.test.yml"),
            "exec", "-T", "-e", "PGPASSWORD=casaviva-backup-test", "postgres-test",
            "pg_dump", "-U", "casaviva_backup", "-d", "casaviva_test", "--schema-only", "--no-owner",
        ],
        cwd=repository,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "CREATE TABLE" in result.stdout
