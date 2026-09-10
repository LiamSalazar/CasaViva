# Migración Pilot PostgreSQL a RDS

1. Acordar ventana y backup/rollback.
2. Poner el sitio en mantenimiento y detener escrituras.
3. Ejecutar `pg_dump` como `casaviva_backup` y verificar checksum.
4. Habilitar/revisar módulo RDS PostgreSQL 18 Single-AZ privado, cifrado, autoscaling de storage, backups y SG sólo desde app.
5. Restaurar con `pg_restore`, crear/verificar roles.
6. Ejecutar `migrate`, `harden_database_roles` y comprobar `casaviva_app`/`casaviva_migrator`.
7. Cambiar `DATABASE_URL` SecureString con SSL requerido.
8. Ejecutar readiness, health y smoke tests; reabrir escrituras.
9. Rollback: volver a mantenimiento, restaurar la URL anterior, reconciliar cualquier escritura permitida por error y levantar Pilot. No destruir la DB anterior hasta aceptación formal.
