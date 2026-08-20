# Seguridad

- Acceso: correo + contraseña hasheada por Django + TOTP obligatorio.
- Recovery codes aleatorios, almacenados como SHA-256 y mostrados una vez.
- Sesión server-side; cookie `Secure`, `HttpOnly`, `SameSite=Lax` en producción; CSRF activo.
- `AuthorizationVersionMiddleware` cierra sesiones cuando cambian accesos.
- Django Admin no es la interfaz normal ni se enlaza desde CasaViva. Está deshabilitado por defecto; `ENABLE_TECHNICAL_ADMIN=true` habilita `/_technical-admin/` sólo para un superusuario con MFA reciente.
- Producción exige secreto, hosts explícitos, HTTPS, HSTS configurable, `DENY`, no-sniff, referrer policy y CSP.
- Request ID en respuesta, log y auditoría; no se registran passwords, códigos, cookies ni tokens.
- Límites separados para login, consultas, tracking y búsqueda.
- Uploads por límite, magic bytes/MIME y reprocesamiento con Pillow.
- Serializers públicos dedicados nunca devuelven comisión, notas, referencia interna, actores, permisos o clientes.

`ANTIBOT_ENABLED` deja el punto de integración para Turnstile. Producción debe sumar rate limiting perimetral.
