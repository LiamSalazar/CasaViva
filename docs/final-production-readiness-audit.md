# Auditoría final de preparación para producción

Fecha de cierre: 2026-09-23. Un estado sólo cambia a `DONE` con una prueba o
inspección verificable.

| ID | Severidad | Subsistema | Corrección/evidencia | Estado |
| --- | --- | --- | --- | --- |
| PHASE-A | P0 | Verificación integral | `./scripts/verify.sh` terminó `CASAVIVA_VERIFY_EXIT=0`; backend coverage 188 passed/5 skipped (86.44%), PostgreSQL 191 passed/2 skipped y Playwright 38/38 PASS, sin `error-context.md`. | DONE |
| E2E-01 | P0 | Turnstile público | Settings de prueba reevalúan el token sólo bajo la base aislada; válido POST→201→confirmación e inválido POST→400→rechazo. No se aceptan tokens ausentes ni se relaja producción. | DONE |
| E2E-02 | P0 | Estado E2E | Throttles elevados únicamente con `CASAVIVA_E2E=1` en `casaviva_test`; fixtures de login/inquiry ya no dependen de residuos entre intentos. | DONE |
| E2E-03 | P1 | Navegación/harness Next dev | Admin/content y analytics esperan marcadores semánticos de shell/provider; el readiness prewarm evita compilación fría y el test de propiedad espera URL/listado funcional, sin internals RSC. | DONE |
| AUTH-01 | P0 | Hidratación de login | El helper espera hidratación React; los formularios tienen `method=post` como fallback para impedir que un submit nativo exponga credenciales en URL. | DONE |
| DB-01 | P0 | PostgreSQL | Persistencia verificada a través de first boot, restart, down/up y recreación. Backup checksum y restore se probaron únicamente sobre PostgreSQL aislado. | DONE |
| OPS-01 | P0 | Despliegue/rollback | Bundle checksum/current-previous, fallo de candidato y rollback manual verificados localmente; las migraciones no se revierten. | DONE |
| TF-01 | P0 | Terraform | `fmt -check`, validate de bootstrap/Pilot y tflint PASS; Checkov 112 passed, 0 failed, 4 skips documentados (KMS policy grammar y monitoring básico Pilot). | DONE |
| OPS-03 | P0 | Rehearsal local | `CASAVIVA_REHEARSAL_EXIT=0`, `PASS LOCAL PRODUCTION REHEARSAL`; verify interno 38/38, persistencia PostgreSQL, backup/restore, ops bundle y rollback PASS. | DONE |
| CI-01 | P0 | CI/CD | CI exacto del release `3ae67d4a...` SUCCESS; Deploy Pilot manual-only con concurrencia `casaviva-production-deploy`, `cancel-in-progress=false`. | DONE |
| AWS-01 | P0 | Cuenta, DNS y state remoto | Preflight AWS con `casaviva-deploy`; Route53, dominio, backend remoto y recursos Pilot verificados sin cambios adicionales. | DONE |
| PLAN-01 | P0 | Plan Terraform | Pilot plan remoto: `No changes`, detailed exit code 0; no drift. | DONE |
| OPS-02 | P0 | Pilot real | EC2/SSM/IAM/OIDC, EBS/KMS, S3 privado, PostgreSQL, backups, CloudWatch, DNS y TLS públicos verificados. | DONE |
| DEPLOY-01 | P0 | Deploy/rollback/restore | Deploy fix, rollback real con ECR JIT y restore final exitosos; migraciones no se revierten y el estado current/previous queda coherente. | DONE |

## Restricciones mantenidas

- Pilot se limita a EC2 ARM64, EBS cifrado para PostgreSQL, S3 privado, ECR,
  IAM/OIDC, SSM, CloudWatch y Budget; no crea NAT Gateway, RDS, ALB, ECS ni
  Growth.
- Ningún secreto AWS ni `tfvars` con secretos se guarda en el repositorio.
- No se ejecutó Terraform apply ni se cambió DNS durante este cierre.
- El dominio público validado es `casaviva-hogar.com`, con `www` redirigido al
  apex y HSTS conservador de una hora.
