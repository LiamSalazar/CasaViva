# Auditoría final de preparación para producción

Fecha de última ejecución: 2026-09-16. Base de esta iteración: `7d2181a`. Un estado sólo cambia a DONE con prueba o inspección verificable; las comprobaciones que requieren servicios AWS permanecen bloqueadas hasta el rehearsal real.

| ID | Severidad | Subsistema | Problema | Evidencia | Corrección | Test | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DB-01 | P0 | PostgreSQL | PGDATA/mount ambiguo en 18 | Compose montaba `/var/lib/postgresql/data` | PGDATA 18 explícito y montaje del padre | `verify.sh`: first boot y persistencia PostgreSQL 18 | DONE |
| DB-02 | P0 | Credenciales | Runtime/migrator compartían entorno | deploy usaba `DATABASE_URL` implícita | APP/MIGRATOR/BACKUP URLs y `current_user` | roles PostgreSQL + deploy inspection | DONE |
| DEP-01 | P0 | First boot | Dependía de `/opt/casaviva/source` | script anterior hacía `cp` desde source | user-data instala bin/config/estructura completa | Terraform validate | DONE |
| DEP-02 | P0 | Deploy/rollback | Recuperación incompleta tras migraciones | `set -e` podía abandonar candidato | trap post-migration, metadata app/ops y rollback sin revertir DB | `rehearse-deployment-rollback.sh`: fallo B y rollback manual | DONE |
| DEP-03 | P0 | First install | Readiness exigía datos que una base nueva aún no puede tener | secuencia deploy/readiness | bootstrap TLS privado por loopback+SSM; normal deploy conserva readiness estricto | test readiness FAIL→PASS + inspección script | DONE |
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
| OPS-01 | P0 | Backup runtime | timer referenciaba `backup.env` antes de materializarlo | user-data + deploy | first/deploy crean 0600, habilitan/verifican timer; verificador EC2 dedicado | local estructural DONE; systemd real requiere AWS | BLOCKED — REQUIRES AWS PILOT REHEARSAL |
| OPS-02 | P0 | Rollback | Fallos post-migration podían salir sin recuperación | inspección del script | trap deliberado cubre arranque/health/Caddy/HTTPS | rehearsal local A/B/rollback | DONE |
| OPS-03 | P0 | Ops bundle | EC2 existente no recibía scripts/config nuevos | `user_data_replace_on_change=false` | tarball por SHA, checksum, S3 privado, instalación atómica y current/previous | `test-ops-bundle.sh` | DONE |
| TLS-01 | P0 | DNS/TLS first install | HTTPS público se exigía antes de DNS | deploy + runbook | health interno, wait DNS acotado y Caddy público sólo después | DNS rehearsal local; TLS real requiere AWS | BLOCKED — REQUIRES AWS PILOT REHEARSAL |
| UI-01 | P0/P1 | About/SiteSettings | Faltaban editores administrativos completos | inspección rutas/componentes | Nosotros + media; Identidad/contacto con permiso sensible y before/after audit | backend tests verdes; E2E completo pendiente de suite final | EN PRUEBA |
| BOT-01 | P0/P1 | Turnstile | El frontend no cargaba ni enviaba/reiniciaba token | `rg` frontend/backend | widget reusable, build-time public config y mock sin red | unit 4 estados; E2E pendiente de suite final | EN PRUEBA |
| ANA-01 | P1 | Analítica | Eventos antes de elección y estado `ESSENTIAL` incorrecto | provider/serializer | no tracking previo o LIMITED; `SESSION_ANALYTICS` tras aceptación; migración histórica | backend + E2E preferencia pendientes de suite final | EN PRUEBA |
