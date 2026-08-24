# Lista de preparación para producción

- [ ] Dominio y DNS configurados.
- [ ] HTTPS y reverse proxy same-origin para Next, `/api/` y media.
- [ ] Secretos fuera de Git y settings de producción seleccionados.
- [ ] Hosts y orígenes CSRF explícitos.
- [ ] PostgreSQL externo y roles técnicos creados.
- [ ] SSL de PostgreSQL comprobado.
- [ ] Migraciones ejecutadas con `casaviva_migrator`.
- [ ] `harden_database_roles` ejecutado después de migrar.
- [ ] `seed_system` ejecutado; catálogo inicial sólo si se desea.
- [ ] Storage S3-compatible y URLs de media comprobados.
- [ ] Founders configurados una sola vez y MFA verificado.
- [ ] Backup externo y restore probados.
- [ ] Healthchecks live/ready correctos.
- [ ] `./scripts/verify.sh` verde.
- [ ] Smoke test público, admin, CRM y BI completado.
