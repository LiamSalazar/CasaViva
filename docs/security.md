# Seguridad

- Acceso: correo + contraseña hasheada por Django + TOTP obligatorio.
- Recovery codes de 128 bits, almacenados con `make_password` de Django y mostrados una vez; cada código se consume una sola vez.
- Sesión server-side; cookie `Secure`, `HttpOnly`, `SameSite=Lax` en producción; CSRF activo.
- `AuthorizationVersionMiddleware` cierra sesiones cuando cambian accesos.
- Django Admin no es la interfaz normal ni se enlaza desde CasaViva. Está deshabilitado por defecto; `ENABLE_TECHNICAL_ADMIN=true` habilita `/_technical-admin/` sólo para un superusuario con MFA reciente.
- Producción exige secreto, hosts explícitos, HTTPS, HSTS configurable, `DENY`, no-sniff, referrer policy y CSP.
- Request ID en respuesta, log y auditoría; no se registran passwords, códigos, cookies ni tokens.
- Límites separados para login, consultas, tracking y búsqueda.
- Uploads por límite, magic bytes/MIME y reprocesamiento con Pillow.
- Serializers públicos dedicados nunca devuelven comisión, notas, referencia interna, actores, permisos o clientes.

`ANTIBOT_ENABLED` deja el punto de integración para Turnstile. Producción debe sumar rate limiting perimetral.

## MFA y sesiones sensibles

El primer acceso sin dispositivo confirmado permite crear un TOTP y exige confirmarlo antes de iniciar la sesión. Si ya existe un dispositivo confirmado, conocer la contraseña no permite enrolar otro: el usuario debe verificar el segundo factor existente. `verify_mfa` sólo usa el dispositivo confirmado para accesos posteriores. El reinicio MFA elimina dispositivos y recovery codes, incrementa `authz_version` y revoca sesiones.

Las operaciones de usuarios, permisos, hard delete y reset MFA usan el helper central `has_recent_mfa`; un timestamp ausente, ilegible o con más de 15 minutos produce 403. Cambiar rol, permisos, estado, contraseña o MFA invalida las sesiones afectadas mediante `authz_version` y eliminación de sesiones server-side.

## Roles PostgreSQL e inmutabilidad

`docker/postgres/init-roles.sh` crea roles sin `SUPERUSER`, `CREATEDB` ni `CREATEROLE`. El comando idempotente `harden_database_roles` puede aplicarse tanto a una instalación nueva como existente:

- `casaviva_app`: CRUD operacional, salvo que en `audit_auditevent` sólo conserva `SELECT` e `INSERT`;
- `casaviva_migrator`: propietario del esquema y único usuario destinado a migraciones;
- `casaviva_readonly`: sólo `SELECT` para BI externo futuro;
- `casaviva_backup`: `SELECT` de tablas/secuencias, suficiente para `pg_dump`, sin escritura.

La suite PostgreSQL se conecta como cada rol real y comprueba permisos positivos y negativos, flags de clúster, inmutabilidad de auditoría y un `pg_dump` real. Estos controles no se simulan con mocks.

El hardening se ejecuta obligatoriamente después de cada `migrate` y antes de seeds o tráfico. Los permisos de marketing separan lectura de BI/marketing de la administración de campañas y gasto; Founder Admin y Owner conservan gestión, mientras un analista con sólo `analytics.view_bi` no puede escribir. Inquiry, Visit y Sale no exponen DELETE CRUD ordinario. Las ventas cambian entre `CLOSED` y `CANCELLED` mediante un servicio transaccional auditado que mantiene la etapa del lead coherente.
