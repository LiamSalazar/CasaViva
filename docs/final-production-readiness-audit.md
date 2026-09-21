# Auditoría final de preparación para producción

Fecha de evidencia local: 2026-09-20. Un estado sólo cambia a `DONE` con una
prueba o inspección verificable. Las operaciones que requieren AWS permanecen
bloqueadas hasta el preflight, plan y rehearsal reales.

| ID | Severidad | Subsistema | Corrección/evidencia | Estado |
| --- | --- | --- | --- | --- |
| PHASE-A | P0 | Verificación integral | `./scripts/verify.sh` terminó `CASAVIVA_VERIFY_EXIT=0`; backend coverage 188 passed/5 skipped (86.44%), PostgreSQL 191 passed/2 skipped y Playwright 38/38 PASS, sin `error-context.md`. | DONE |
| E2E-01 | P0 | Turnstile público | Settings de prueba reevalúan el token sólo bajo la base aislada; válido POST→201→confirmación e inválido POST→400→rechazo. No se aceptan tokens ausentes ni se relaja producción. | DONE |
| E2E-02 | P0 | Estado E2E | Throttles elevados únicamente con `CASAVIVA_E2E=1` en `casaviva_test`; fixtures de login/inquiry ya no dependen de residuos entre intentos. | DONE |
| E2E-03 | P1 | Navegación RSC | Admin y Favoritos esperan su respuesta RSC 200 antes de URL/contenido. Traces confirmaron handler, 200 y render correcto; Fast Refresh de Next dev difería el commit de URL. | DONE |
| AUTH-01 | P0 | Hidratación de login | El helper espera hidratación React; los formularios tienen `method=post` como fallback para impedir que un submit nativo exponga credenciales en URL. | DONE |
| DB-01 | P0 | PostgreSQL | Persistencia verificada a través de first boot, restart, down/up y recreación. Backup checksum y restore se probaron únicamente sobre PostgreSQL aislado. | DONE |
| OPS-01 | P0 | Despliegue/rollback | Bundle checksum/current-previous, fallo de candidato y rollback manual verificados localmente; las migraciones no se revierten. | DONE |
| TF-01 | P0 | Terraform | `fmt -check`, validate de bootstrap/Pilot y tflint PASS; Checkov 112 passed, 0 failed, 4 skips documentados (KMS policy grammar y monitoring básico Pilot). | DONE |
| CI-01 | P0 | CI/CD | Debe validarse CI remoto para el SHA exacto que se publique. | PENDIENTE |
| AWS-01 | P0 | Cuenta, DNS y state remoto | Faltan identidad perfil `casaviva-deploy`, región, Route53/hosted zone, recursos existentes y backend Terraform. | PENDIENTE |
| PLAN-01 | P0 | Plan Terraform | Falta plan real bootstrap/Pilot y revisión de create/change/destroy, ausencia de NAT/RDS/ALB/ECS/Growth y costo. | PENDIENTE |
| OPS-02 | P0 | Pilot real | IMDSv2/IAM, S3, systemd, KMS/EBS, SSM y DNS/TLS públicos requieren rehearsal AWS. | BLOCKED — REQUIRES AWS PILOT REHEARSAL |

## Restricciones mantenidas

- Pilot se limita a EC2 ARM64, EBS cifrado para PostgreSQL, S3 privado, ECR,
  IAM/OIDC, SSM, CloudWatch y Budget; no crea NAT Gateway, RDS, ALB, ECS ni
  Growth.
- Ningún secreto AWS ni `tfvars` con secretos se guarda en el repositorio.
- No se ejecutó Terraform apply ni se cambió DNS.
