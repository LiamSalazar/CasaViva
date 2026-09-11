# Auditoría final de preparación para producción

Fecha: 2026-09-11. Estado inicial limpio (`git status --short` sin salida), commits revisados: `450f91f NOMS_ARCO_TERRA` y `e115630` CI/CD + Checkov. Un estado sólo cambia a DONE con prueba o inspección verificable.

| ID | Severidad | Subsistema | Problema | Evidencia | Corrección | Test | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DB-01 | P0 | PostgreSQL | PGDATA/mount ambiguo en 18 | Compose montaba `/var/lib/postgresql/data` | PGDATA 18 explícito y montaje del padre | `test-postgres-persistence.sh` | EN PRUEBA |
| DB-02 | P0 | Credenciales | Runtime/migrator compartían entorno | deploy usaba `DATABASE_URL` implícita | APP/MIGRATOR/BACKUP URLs y `current_user` | roles PostgreSQL + deploy inspection | DONE |
| DEP-01 | P0 | First boot | Dependía de `/opt/casaviva/source` | script anterior hacía `cp` desde source | user-data instala bin/config/estructura completa | Terraform validate | DONE |
| DEP-02 | P0 | Deploy/rollback | Sin lock, project estable ni rollback ejecutable | script anterior requería account ID | lock, STS, SHA, project `casaviva`, metadata y rollback | rehearsal pendiente | EN PRUEBA |
| AWS-01 | P0 | Datos | PostgreSQL vivía en root EBS | compute sólo definía root | EBS gp3 cifrado separado y montaje por UUID | Terraform validate/plan | EN PRUEBA |
| BAK-01 | P0 | Backups | Script sin timer/checksum/retención válida | lifecycle global 90 días | timer, checksum, daily/weekly/monthly 15/60/370 | restore aislado | EN PRUEBA |
| CI-01 | P0 | CI/CD | CI no creaba `.venv`; CD paralelo | workflows inspeccionados | venv y `workflow_run` exitoso; QEMU/Buildx ARM64 | inspección YAML/CI remota | EN PRUEBA |
| APP-01 | P0 | Listings | Edición publicada omitía invariantes | relation cache y transición solamente | validación del agregado actualizado + filtro defensivo público | tres regresiones requeridas | EN PRUEBA |
| LEG-01 | P0 | Legal | Cualquier corchete bloqueaba Markdown | `legal_services.py` | placeholders explícitos | unit test | EN PRUEBA |
| LEG-02 | P0 | Readiness legal | Legacy podía satisfacer check | query sólo PUBLISHED/active | `production_ready` explícito + hash/fechas/contenido | migration/tests | EN PRUEBA |
| API-01 | P1 | Legal pública | Serializer administrativo público | hashes/IDs/actor expuestos | serializer público mínimo | API test | EN PRUEBA |
| CSP-01 | P0 | Caddy/Next | `script-src 'self'` rompe hidratación inline | Caddyfile | CSP Pilot compatible sin unsafe-eval | Playwright/Caddy | EN PRUEBA |
| ENV-01 | P0 | Verificación | Suite base no alcanza umbral | 171 passed, 5 skipped, coverage 83.51% | pendiente ampliar cobertura o política justificada | `./scripts/verify.sh` | FAIL |
