# Despliegue

```text
https://casaviva.mx/          -> Next.js
https://casaviva.mx/api/v1/   -> Django
https://casaviva.mx/media/    -> storage/CDN autorizado
```

1. Crear secretos fuera de Git y roles equivalentes a `docker/postgres/init-roles.sh`.
2. Migrar con `casaviva_migrator`; servir con `casaviva_app`, nunca `postgres`.
3. Compilar Next con API relativa.
4. Configurar TLS, hosts, CSRF, HSTS progresivo y límites perimetrales.
5. Servir media bloqueando ejecución/sniffing.
6. Desactivar documentación interactiva y admin técnico.
7. Ejecutar smoke tests de home, búsqueda, ficha, consulta, MFA, publicación y BI.

No activar HSTS preload antes de confirmar todos los subdominios. Se persiste UTC y se muestra `America/Mexico_City`.
