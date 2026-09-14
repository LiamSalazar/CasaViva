# Auditoría final de preparación para producción

Fecha de última ejecución: 2026-09-14. Estado base revisado en `da09f82`; también se inspeccionaron los traces Playwright adjuntos del run CI #2. Un estado sólo cambia a DONE con prueba o inspección verificable.

| ID | Severidad | Subsistema | Problema | Evidencia | Corrección | Test | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DB-01 | P0 | PostgreSQL | PGDATA/mount ambiguo en 18 | Compose montaba `/var/lib/postgresql/data` | PGDATA 18 explícito y montaje del padre | `verify.sh`: first boot y persistencia PostgreSQL 18 | DONE |
| DB-02 | P0 | Credenciales | Runtime/migrator compartían entorno | deploy usaba `DATABASE_URL` implícita | APP/MIGRATOR/BACKUP URLs y `current_user` | roles PostgreSQL + deploy inspection | DONE |
| DEP-01 | P0 | First boot | Dependía de `/opt/casaviva/source` | script anterior hacía `cp` desde source | user-data instala bin/config/estructura completa | Terraform validate | DONE |
| DEP-02 | P0 | Deploy/rollback | Sin lock, project estable ni rollback ejecutable | script anterior requería account ID | lock, STS, SHA, project `casaviva`, metadata y rollback | rehearsal pendiente | EN PRUEBA |
| AWS-01 | P0 | Datos | PostgreSQL vivía en root EBS | compute sólo definía root | EBS gp3 cifrado separado y montaje por UUID | Terraform validate/plan | EN PRUEBA |
| BAK-01 | P0 | Backups | Script sin timer/checksum/retención válida | lifecycle global 90 días | timer, checksum, daily/weekly/monthly 15/60/370 | restore aislado | EN PRUEBA |
| CI-01 | P0 | CI/CD | CI no creaba `.venv`; CD podía dispararse manualmente sin un CI asociado | workflows inspeccionados | venv, `workflow_run` exitoso como único trigger; QEMU/Buildx ARM64 | `verify.sh` local GREEN + inspección YAML; run remoto nuevo pendiente de push | EN PRUEBA |
| APP-01 | P0 | Listings | Edición publicada omitía invariantes | relation cache y transición solamente | validación del agregado actualizado + filtro defensivo público | tres regresiones requeridas | EN PRUEBA |
| LEG-01 | P0 | Legal | Cualquier corchete bloqueaba Markdown | `legal_services.py` | placeholders explícitos | unit test | EN PRUEBA |
| LEG-02 | P0 | Readiness legal | Legacy podía satisfacer check | query sólo PUBLISHED/active | `production_ready` explícito + hash/fechas/contenido | migration/tests | EN PRUEBA |
| API-01 | P1 | Legal pública | Serializer administrativo público | hashes/IDs/actor expuestos | serializer público mínimo | API test | EN PRUEBA |
| CSP-01 | P0 | Caddy/Next | `script-src 'self'` rompe hidratación inline | Caddyfile | CSP Pilot compatible sin unsafe-eval | Playwright/Caddy | EN PRUEBA |
| ENV-01 | P0 | Verificación | Suite del run CI #2 tenía fallos E2E deterministas | traces adjuntos y primera reproducción: 23 pass/8 fail | selectores/consentimientos vigentes, fixtures publicables, identidad session-only y storageState MFA por usuario | `./scripts/verify.sh`: unit 176 pass, PostgreSQL 180 pass, Playwright 31 pass | DONE |
| TF-01 | P0 | Terraform/Checkov | CKV_AWS_300 y CKV_AWS_189; CKV_AWS_126 incompatible con objetivo de costo Pilot | Checkov del run CI #2 | abort multipart 7 días, CMK rotada `alias/casaviva-pilot`, EBS cifrados; skip motivado sólo para detailed monitoring | fmt/validate/tflint y Checkov 112 pass, 0 fail | DONE |
| OPS-01 | P0 | Backup runtime | timer referenciaba `backup.env` que nunca se materializaba | user-data + unit systemd | deploy genera archivo 0600 desde SSM y valida rol/URI | sintaxis shell; rehearsal AWS pendiente | EN PRUEBA |
| OPS-02 | P0 | Rollback | `set -e` evitaba rollback si fallaba `compose up --wait` | inspección del script | fallo de arranque entra explícitamente a rollback | sintaxis shell; rehearsal de fallo pendiente | EN PRUEBA |
| OPS-03 | P0 | Ops bundle | cambios posteriores de scripts/config no se distribuyen a una EC2 ya creada porque `user_data_replace_on_change=false` | inspección Terraform/CD | pendiente canal firmado/versionado de actualización del bundle | pendiente | FAIL |
| TLS-01 | P0 | DNS/TLS first install | deploy exige health HTTPS del dominio antes de que la secuencia documentada configure DNS | deploy + runbook | pendiente separar health interno/pre-DNS y validación pública post-DNS | pendiente | FAIL |
| UI-01 | P0/P1 | About/SiteSettings | APIs existen, pero no hay editor completo de About y SiteSettings sólo expone contacto/redes | inspección rutas/componentes | pendiente UI completa, permisos sensibles y E2E | pendiente | FAIL |
| BOT-01 | P0/P1 | Turnstile | verificador backend existe, frontend no carga widget ni envía/reinicia token | `rg` frontend/backend | pendiente integración UI y E2E mock | pendiente | FAIL |
