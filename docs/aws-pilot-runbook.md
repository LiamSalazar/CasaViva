# Runbook AWS Pilot

Este runbook es el camino operativo vigente. Pilot usa una EC2 `t4g.small`, PostgreSQL 18 local sobre EBS separado, buckets S3 privados, ECR, SSM y CloudWatch Agent en el host. No crea NAT, ALB, ECS ni RDS. Los pasos AWS de este documento requieren aprobación humana y no forman parte de la verificación local.

## Phase 1 — Terraform bootstrap

```bash
aws sts get-caller-identity
aws configure get region  # debe ser mx-central-1
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap plan -out=bootstrap.tfplan -var='state_bucket_name=REEMPLAZAR'
terraform -chdir=infra/bootstrap apply bootstrap.tfplan  # NO ejecutar sin aprobación
```

## Phase 2 — plan y apply de Pilot

Copiar `infra/environments/pilot/terraform.tfvars.example` fuera de Git, usar una AMI AL2023 ARM64 vigente y dos AZ realmente disponibles.

```bash
terraform -chdir=infra/environments/pilot init \
  -backend-config='bucket=REEMPLAZAR' \
  -backend-config='key=pilot/terraform.tfstate' \
  -backend-config='region=mx-central-1' \
  -backend-config='encrypt=true' \
  -backend-config='use_lockfile=true'
terraform -chdir=infra/environments/pilot plan -out=pilot.tfplan -var-file=/RUTA/SEGURA/pilot.tfvars
terraform -chdir=infra/environments/pilot show pilot.tfplan
terraform -chdir=infra/environments/pilot apply pilot.tfplan  # NO ejecutar sin aprobación
```

El plan debe mostrar EC2 ARM64, EIP, root EBS y PostgreSQL EBS cifrados con `alias/casaviva-pilot`, buckets privados, ECR, OIDC/IAM, SSM, métricas/alarmas y Budget; debe mostrar cero NAT, ALB, RDS, ECS y Growth.

## Phase 3 — parámetros y DNS

Obtener `instance_id`, `public_ip`, buckets y repositorios con `terraform output`. Crear los parámetros `/casaviva-pilot/*` mediante `aws ssm put-parameter --type SecureString`; nunca poner secretos en tfvars ni Git. El conjunto mínimo es:

- `DJANGO_SECRET_KEY`, `POSTGRES_SUPERUSER_PASSWORD`;
- `APP_DATABASE_PASSWORD`, `MIGRATOR_DATABASE_PASSWORD`, `BACKUP_DATABASE_PASSWORD`, `READONLY_DATABASE_PASSWORD`;
- `PUBLIC_DOMAIN`, `ACME_EMAIL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`;
- `STORAGE_BACKEND=s3`, `S3_BUCKET_NAME`, `MEDIA_REMOTE_HOSTNAME`, `BACKUP_S3_URI`;
- configuración de email; `ANTIBOT_ENABLED`, `TURNSTILE_SECRET_KEY` y `NEXT_PUBLIC_TURNSTILE_SITE_KEY` si se activa (la misma site key pública se configura también como variable de build de GitHub);
- correos y contraseñas iniciales `LIAM_*`, `ANA_*`, `ALFREDO_*` sólo hasta ejecutar el bootstrap.

Las contraseñas de base se almacenan como componentes. `render-pilot-env.py` construye URLs con percent-encoding y serializa dotenv sin exponerlas en logs.

Crear el registro A del dominio hacia la EIP. Confirmar antes del despliegue público:

```bash
./scripts/wait-for-dns.sh casaviva-hogar.com EIP_ESPERADA 600
```

Si aún no coincide, el resultado correcto es `DNS_NOT_READY`; Caddy público no se inicia.

## Phase 4 — first install privado

Configurar el GitHub Environment `production` con aprobación y las variables `AWS_DEPLOY_ROLE_ARN`, `PILOT_INSTANCE_ID`, `OPS_BUCKET_NAME` (bucket privado de backup), `MEDIA_REMOTE_HOSTNAME`, `ANTIBOT_ENABLED` y `TURNSTILE_SITE_KEY`. `Deploy Pilot` vuelve a comprobar CI exitoso para el SHA exacto, construye imágenes ARM64, crea `casaviva-ops-<SHA>.tar.gz` y checksum, los publica bajo `s3://OPS_BUCKET_NAME/ops/<SHA>/`, instala el bundle atómicamente y ejecuta `first-install-pilot.sh` cuando no existe `bootstrap_release`.

First install ejecuta `migrate → harden_database_roles → seed_system`, comprueba `casaviva_app` y levanta Caddy únicamente en `127.0.0.1:8443` con TLS interno. Los puertos públicos permanecen sin listener.

## Phase 5 — founders, MFA e información legal

Abrir un túnel SSM (sin SSH):

```bash
aws ssm start-session --region mx-central-1 --target INSTANCE_ID \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8443"],"localPortNumber":["8443"]}'
```

En otra terminal ejecutar founders una sola vez:

```bash
aws ssm send-command --region mx-central-1 --instance-ids INSTANCE_ID \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["sudo docker compose -p casaviva --env-file /opt/casaviva/current/.env.production -f /opt/casaviva/current/docker-compose.yml -f /opt/casaviva/current/docker-compose.bootstrap.yml exec -T backend python manage.py bootstrap_founders"]'
```

Abrir `https://localhost:8443/administracion/acceso`, aceptar únicamente el certificado local de este túnel, completar MFA y configurar desde UI `Contenido → Identidad y contacto`, `Contenido → Nosotros`, Aviso de Privacidad y Términos. No inventar domicilio, correos ni teléfono.

Después de crear y comprobar las cuentas, eliminar de Parameter Store los parámetros `LIAM_PASSWORD`, `ANA_PASSWORD` y `ALFREDO_PASSWORD` (y sus correos si no se necesitan operativamente). El siguiente deploy regenerará el entorno sin esas credenciales iniciales; `bootstrap_founders` no vuelve a ejecutarse automáticamente.

## Phase 6 — readiness

```bash
sudo docker compose -p casaviva --env-file /opt/casaviva/current/.env.production \
  -f /opt/casaviva/current/docker-compose.yml -f /opt/casaviva/current/docker-compose.bootstrap.yml \
  exec -T backend python manage.py check_production_readiness
```

`FAIL` mantiene el bootstrap privado. `WARN` no cambia el exit code. Sólo `PASS` permite continuar.

## Phase 7 — HTTPS público

Ejecutar manualmente `Deploy Pilot` para el mismo SHA validado. Como `bootstrap_release` ya existe, se usa el flujo normal: readiness, health interno, DNS, validación Caddy, arranque público y health HTTPS. Sólo al terminar se crea `first_install_complete`.

## Phase 8 — backup y restore

```bash
sudo /opt/casaviva/bin/verify-backup-systemd.sh
sudo systemctl start casaviva-postgres-backup.service
sudo systemctl status casaviva-postgres-backup.service --no-pager
```

Descargar el último dump/checksum y ejecutar `scripts/test-postgres-restore.sh` contra PostgreSQL aislado. Nunca restaurar sobre Pilot.

## Phase 9 — IAM/IMDSv2

Definir un bucket ajeno de prueba al que deba denegarse acceso y ejecutar por SSM:

```bash
sudo AWS_DENY_TEST_BUCKET=BUCKET_NO_AUTORIZADO /opt/casaviva/bin/verify-aws-runtime-access.sh
```

Debe confirmar credenciales temporales desde el backend container, Put/Get/Delete en media y denegación fuera de alcance, sin imprimir tokens.

## Phase 10 — segundo deploy

Fusionar un commit inocuo con CI verde, aprobar `production` y comprobar imágenes/bundle del mismo SHA, `current_release`, `previous_release`, `current_ops_release`, health y smoke.

## Phase 11 — rollback

```bash
aws ssm send-command --region mx-central-1 --instance-ids INSTANCE_ID \
  --document-name AWS-RunShellScript --parameters 'commands=["sudo /opt/casaviva/bin/rollback.sh"]'
```

Debe restaurar aplicación y bundle operativo previos y repetir health/smoke. No revierte migraciones; todos los cambios DB del periodo deben cumplir `database-migration-safety.md`.

## Phase 12 — decisión GO

Registrar evidencia de KMS/EBS, SSM, IAM container, media S3, timer/backup/restore, DNS/TLS, deploy 1/2, rollback, alarmas, Budget y smoke. Hasta completar estas pruebas el estado es `BLOCKED — REQUIRES AWS PILOT REHEARSAL`, no GO para tráfico público.
