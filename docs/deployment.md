# Despliegue

Para AWS Pilot use [aws-pilot-runbook.md](aws-pilot-runbook.md), que es la fuente operativa principal. El primer install es privado mediante SSM; un deploy normal sólo expone Caddy después de readiness, health interno y DNS. CI publica imágenes ARM64 y un bundle operativo privado del mismo SHA; la EC2 verifica su checksum y conserva las versiones current/previous para rollback. Nunca se usa SSH público ni claves AWS persistentes.

## Desarrollo local

El flujo breve y los comandos mantenidos están al inicio de `README.md`. Usa PostgreSQL de Docker, almacenamiento local y nunca el rol migrator para servir `runserver`.

## Producción

```text
https://casaviva.mx/          -> Next.js
https://casaviva.mx/api/v1/   -> Django
https://casaviva.mx/media/    -> storage/CDN autorizado
```

1. Crear secretos fuera de Git. En Pilot se guardan componentes de contraseña en Parameter Store y se construyen URLs percent-encoded; no se guardan claves AWS.
2. Conectar como `casaviva_migrator` y ejecutar `python backend/manage.py migrate`.
3. Sin cambiar todavía de rol, ejecutar el comando idempotente y obligatorio `python backend/manage.py harden_database_roles`. Esto revoca `UPDATE/DELETE` de auditoría al rol de aplicación y fija los grants de readonly/backup.
4. Conectar como `casaviva_app` y ejecutar `seed_system`. `seed_reference_catalog` es opcional. Ejecutar `bootstrap_founders` una sola vez.
5. Servir requests con `casaviva_app`, nunca con `postgres` ni con `casaviva_migrator`.
6. Compilar Next con API relativa y desplegar los Dockerfiles de `docker/` o procesos equivalentes. Con media remota pasar `--build-arg MEDIA_REMOTE_HOSTNAME=media.ejemplo.mx` al Dockerfile frontend: Next fija `remotePatterns` durante el build, no al arrancar el contenedor.
7. Configurar TLS, hosts, CSRF, HSTS progresivo y límites perimetrales.
8. Servir media bloqueando ejecución/sniffing.
9. Desactivar documentación interactiva y admin técnico.
10. Ejecutar smoke tests de home, búsqueda, ficha, consulta, MFA, publicación y BI.
11. Comprobar `/api/health/live/` y `/api/health/ready/`.

El orden `migrate → harden_database_roles → seeds/bootstrap → run` forma parte del procedimiento de instalación. Cada despliegue que ejecute nuevas migraciones vuelve a aplicar el hardening antes de servir tráfico.

Comenzar con HSTS en `0`. Tras validar HTTPS avanzar, observando cada etapa, por `300`, `86400`, `604800` y finalmente `31536000`. Activar `includeSubDomains` sólo cuando todos los subdominios relevantes tengan HTTPS. No activar preload sin una decisión explícita posterior. Se persiste UTC y se muestra `America/Mexico_City`.

`APP_DATABASE_URL`, `MIGRATOR_DATABASE_URL` y `BACKUP_DATABASE_URL` tienen funciones separadas. `DB_SSL_REQUIRE=true` se usará al migrar a RDS. Si `STORAGE_BACKEND=s3`, el bucket sigue privado y boto3 obtiene credenciales temporales del Instance Profile mediante IMDSv2; no se configuran access keys ni lectura pública del bucket. CloudFront/OAC permanece opcional y apagado en Pilot.
