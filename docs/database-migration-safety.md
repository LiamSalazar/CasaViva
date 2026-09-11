# Seguridad de migraciones

Orden de primera instalación: PostgreSQL saludable → roles de `init-roles.sh` → `migrate` con `MIGRATOR_DATABASE_URL` (`casaviva_migrator`) → `harden_database_roles` con el mismo rol → `seed_system` con `APP_DATABASE_URL` → `check_production_readiness` con `casaviva_app` → Gunicorn con `APP_DATABASE_URL`. `bootstrap_founders` se ejecuta interactivamente una sola vez y nunca forma parte de deploy.

Un deploy normal repite migraciones, hardening, seed idempotente y readiness, pero no founders. Backup usa exclusivamente `BACKUP_DATABASE_URL` (`casaviva_backup`). El deploy comprueba `current_user=casaviva_app` antes de iniciar tráfico.

Toda migración que deba permitir rollback de aplicación sigue expand/contract: primero añadir estructuras compatibles y escribir ambos formatos; después migrar datos/lecturas; eliminar columnas o constraints antiguos en un release posterior, cuando la versión anterior ya no sea candidata de rollback. `rollback.sh` cambia imágenes y configuración; nunca revierte migraciones automáticamente.
