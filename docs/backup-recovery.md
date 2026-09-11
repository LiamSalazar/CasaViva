# Backups y recuperación

- `pg_dump` diario con `casaviva_backup`, cifrado fuera del host.
- La retención debe configurarse y aprobarse; el software no la presenta como plazo legal.
- Object storage con versionado y copia; PostgreSQL solo no basta.
- Restore mensual en entorno aislado verificando listings, ventas, auditoría y hashes.
- Objetivos iniciales: RPO 24 h y RTO 4 h; no son garantía hasta automatizar y ensayar.

Recuperación: congelar escrituras, restaurar DB y objetos en instancias nuevas, ejecutar checks/migraciones/smoke tests, rotar secretos, cambiar tráfico y documentar. Un backup no se declara válido sin restauración probada.

En Pilot, el timer systemd diario ejecuta `scripts/backup-postgres-s3.sh` exclusivamente con `casaviva_backup`, verifica el dump, genera SHA-256 y lo sube cifrado. Promueve domingos y primer día del mes; lifecycle conserva daily 15 días, weekly 60 y monthly 370. `scripts/test-postgres-restore.sh` prueba checksum y restore únicamente en PostgreSQL aislado. Ejecutarlo mensualmente y registrar RPO/RTO.
