# Runbook AWS Pilot

Bootstrap: `cd infra/bootstrap && terraform init && terraform plan -out bootstrap.tfplan -var state_bucket_name=NOMBRE && terraform apply bootstrap.tfplan` (única operación manual autorizada cuando se decida crear AWS).

Configurar backend: `terraform -chdir=infra/environments/pilot init -backend-config="bucket=NOMBRE" -backend-config="key=pilot/terraform.tfstate" -backend-config="region=mx-central-1" -backend-config="encrypt=true" -backend-config="use_lockfile=true"`.

Plan: copiar `terraform.tfvars.example` fuera de Git, resolver dos AZ reales y AMI ARM64; luego `terraform -chdir=infra/environments/pilot plan -out=pilot.tfplan`. Revisar cero NAT/SSH/ASG/RDS/CloudFront, t4g.small, 30 GB cifrado, buckets privados, IAM mínimo, budget y costo antes de cualquier apply.

Secretos: `aws ssm put-parameter --region mx-central-1 --name /casaviva-pilot/DJANGO_SECRET_KEY --type SecureString --value '...' --overwrite`; repetir por contraseñas DB, correo y Turnstile. No poner valores en tfvars.

## Antes de apply

- Confirmar cuenta/región, domicilio, correos, teléfono, AMI ARM64, dos AZ, buckets únicos y destinatarios de alertas.
- Ejecutar `./scripts/verify.sh`, `terraform fmt -check -recursive infra`, `terraform -chdir=infra/environments/pilot validate`, `tflint --chdir=infra/environments/pilot` y `checkov -d infra`.
- Revisar `terraform -chdir=infra/environments/pilot show pilot.tfplan`: cero NAT, SSH, RDS, Growth y CloudFront.

Apply, sólo tras aprobación humana: `terraform -chdir=infra/environments/pilot apply pilot.tfplan`.

## Después de apply y primer despliegue

1. Confirmar alarmas, SNS, Budget, SSM, buckets privados y ECR.
2. Cargar parámetros y comprobar nombres con `aws ssm get-parameters-by-path --path /casaviva-pilot/ --with-decryption`.
3. Configurar environment protegido `production` y `AWS_DEPLOY_ROLE_ARN` en GitHub.
4. Aprobar el job del GitHub Environment `production` cuando `Deploy Pilot` se dispare tras CI exitoso; `workflow_dispatch` queda sujeto al mismo Environment.
5. El CD ejecuta por SSM pull, migraciones, hardening, seed, production check, arranque y health checks.
6. Probar health, portada, búsqueda, ficha, formulario, administración, media y correo de lead.
7. Ejecutar backup y restauración automatizable en una base temporal; registrar RPO/RTO real.

## Rollback

El deploy invoca `/opt/casaviva/bin/rollback.sh` si falla el health check. Para rollback manual ejecute ese archivo mediante SSM y repita `scripts/smoke-production.sh`. No revierte migraciones; siga `database-migration-safety.md`.
