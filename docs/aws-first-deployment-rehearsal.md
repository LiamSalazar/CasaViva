# Ensayo del primer despliegue AWS (no ejecutar automáticamente)

1. Seleccionar cuenta, `mx-central-1`, dos AZ soportadas y AMI Amazon Linux 2023 ARM64.
2. Crear el backend Terraform con los comandos de `aws-pilot-runbook.md` y revisar su plan.
3. Inicializar Pilot y generar `pilot.tfplan`; verificar que no contiene NAT, ALB, RDS, ECS ni Growth.
4. Aplicar sólo con aprobación humana. Terraform crea red, EC2 t4g.small, root EBS, EBS PostgreSQL retenido, EIP, buckets privados, ECR, IAM/OIDC, SSM y monitoreo.
5. User-data instala Docker/SSM/CloudWatch, monta el EBS sin reformatear datos y crea `/opt/casaviva/{bin,config,releases,shared,postgres,logs}`, timer de backup, `deploy.sh` y `rollback.sh`.
6. Cargar Parameter Store, incluida identidad legal real, tres URLs DB separadas, dominio, storage, email y Turnstile si se activa.
7. Configurar GitHub Environment `production`, `AWS_DEPLOY_ROLE_ARN`, `PILOT_INSTANCE_ID` y `MEDIA_REMOTE_HOSTNAME`; requerir aprobación si corresponde.
8. CI verde desencadena Build ARM64 y Deploy por SSM. El host migra/hardening, valida rol app, reemplaza containers del proyecto estable `casaviva` y hace health checks.
9. Ejecutar smoke, backup/restore aislado y rollback; sólo después apuntar `casaviva.mx` y `www` a la EIP. Configurar `media` según URLs firmadas/CloudFront privado.
