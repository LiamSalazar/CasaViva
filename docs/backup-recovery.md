# Backups y recuperación

- `pg_dump` diario con `casaviva_backup`, cifrado fuera del host.
- Retención propuesta: 14 diarios, 8 semanales y 12 mensuales.
- Object storage con versionado y copia; PostgreSQL solo no basta.
- Restore mensual en entorno aislado verificando listings, ventas, auditoría y hashes.
- Objetivos iniciales: RPO 24 h y RTO 4 h; no son garantía hasta automatizar y ensayar.

Recuperación: congelar escrituras, restaurar DB y objetos en instancias nuevas, ejecutar checks/migraciones/smoke tests, rotar secretos, cambiar tráfico y documentar. Un backup no se declara válido sin restauración probada.
