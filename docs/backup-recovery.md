# Backups y recuperación

- `pg_dump` diario con `casaviva_backup`, cifrado fuera del host.
- La retención debe configurarse y aprobarse; el software no la presenta como plazo legal.
- Object storage con versionado y copia; PostgreSQL solo no basta.
- Restore mensual en entorno aislado verificando listings, ventas, auditoría y hashes.
- Objetivos iniciales: RPO 24 h y RTO 4 h; no son garantía hasta automatizar y ensayar.

Recuperación: congelar escrituras, restaurar DB y objetos en instancias nuevas, ejecutar checks/migraciones/smoke tests, rotar secretos, cambiar tráfico y documentar. Un backup no se declara válido sin restauración probada.

En Pilot, `scripts/backup-postgres-s3.sh` usa exclusivamente `casaviva_backup` y sube un custom dump cifrado al bucket privado. `scripts/test-restore-backup.sh` sólo acepta una URL cuya base incluya `casaviva_restore_test`, restaura en aislamiento y verifica tablas críticas. Alertar por fallo y antigüedad del último objeto.
