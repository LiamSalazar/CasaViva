from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Aplica grants mínimos e inmutabilidad de auditoría en PostgreSQL."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stdout.write(self.style.WARNING("Hardening omitido: esta base no es PostgreSQL."))
            return
        roles = {"casaviva_app", "casaviva_readonly", "casaviva_backup"}
        with connection.cursor() as cursor:
            cursor.execute("SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)", [list(roles)])
            present = {row[0] for row in cursor.fetchall()}
            missing = roles - present
            if missing:
                raise CommandError(f"Faltan roles PostgreSQL: {', '.join(sorted(missing))}")
            cursor.execute("GRANT USAGE ON SCHEMA public TO casaviva_app, casaviva_readonly, casaviva_backup")
            cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO casaviva_app")
            cursor.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO casaviva_app")
            cursor.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO casaviva_readonly, casaviva_backup")
            cursor.execute("GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO casaviva_backup")
            cursor.execute("REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_auditevent FROM casaviva_app")
            cursor.execute("GRANT SELECT, INSERT ON TABLE audit_auditevent TO casaviva_app")
        self.stdout.write(self.style.SUCCESS("Roles y auditoría endurecidos."))
