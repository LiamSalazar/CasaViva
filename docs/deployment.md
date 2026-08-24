# Despliegue

## Desarrollo local

El flujo breve y los comandos mantenidos están al inicio de `README.md`. Usa PostgreSQL de Docker, almacenamiento local y nunca el rol migrator para servir `runserver`.

## Producción

```text
https://casaviva.mx/          -> Next.js
https://casaviva.mx/api/v1/   -> Django
https://casaviva.mx/media/    -> storage/CDN autorizado
```

1. Crear secretos fuera de Git y roles equivalentes a `docker/postgres/init-roles.sh`.
2. Conectar como `casaviva_migrator` y ejecutar `python backend/manage.py migrate`.
3. Sin cambiar todavía de rol, ejecutar el comando idempotente y obligatorio `python backend/manage.py harden_database_roles`. Esto revoca `UPDATE/DELETE` de auditoría al rol de aplicación y fija los grants de readonly/backup.
4. Conectar como `casaviva_app` y ejecutar `seed_system`. `seed_reference_catalog` es opcional. Ejecutar `bootstrap_founders` una sola vez.
5. Servir requests con `casaviva_app`, nunca con `postgres` ni con `casaviva_migrator`.
6. Compilar Next con API relativa y desplegar los Dockerfiles de `docker/` o procesos equivalentes. Configurar storage S3-compatible en producción.
7. Configurar TLS, hosts, CSRF, HSTS progresivo y límites perimetrales.
8. Servir media bloqueando ejecución/sniffing.
9. Desactivar documentación interactiva y admin técnico.
10. Ejecutar smoke tests de home, búsqueda, ficha, consulta, MFA, publicación y BI.
11. Comprobar `/api/health/live/` y `/api/health/ready/`.

El orden `migrate → harden_database_roles → seeds/bootstrap → run` forma parte del procedimiento de instalación. Cada despliegue que ejecute nuevas migraciones vuelve a aplicar el hardening antes de servir tráfico.

No activar HSTS preload antes de confirmar todos los subdominios. Se persiste UTC y se muestra `America/Mexico_City`.

`DATABASE_URL` es obligatorio en producción y `DB_SSL_REQUIRE=true` activa SSL sin acoplarse a proveedor. Si `STORAGE_BACKEND=s3`, bucket y credenciales son obligatorios. Los backups deben salir del mismo servidor o cuenta que aloja la aplicación.
