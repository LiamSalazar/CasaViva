# Ensayo del primer despliegue AWS (no ejecutar automáticamente)

1. Seleccionar cuenta, `mx-central-1`, dos AZ soportadas y AMI Amazon Linux 2023 ARM64.
2. Crear el backend Terraform con los comandos de `aws-pilot-runbook.md` y revisar su plan.
3. Inicializar Pilot y generar `pilot.tfplan`; verificar que no contiene NAT, ALB, RDS, ECS ni Growth.
4. Aplicar sólo con aprobación humana. Terraform crea red, EC2 t4g.small, root EBS, EBS PostgreSQL retenido, EIP, buckets privados, ECR, IAM/OIDC, SSM y monitoreo.
5. User-data instala Docker/SSM/CloudWatch Agent del host, monta el EBS sin reformatear datos y crea `/opt/casaviva/{bin,config,releases,ops-releases,shared,postgres,logs}`. El timer no se habilita hasta materializar `backup.env` 0600.
6. Cargar componentes DB, dominio, storage, email y Turnstile en Parameter Store. La identidad legal se completa desde UI, no mediante secretos ni Terraform.
7. Configurar GitHub Environment `production`, `AWS_DEPLOY_ROLE_ARN`, `PILOT_INSTANCE_ID`, `OPS_BUCKET_NAME`, `MEDIA_REMOTE_HOSTNAME`, `ANTIBOT_ENABLED` y `TURNSTILE_SITE_KEY`; requerir aprobación.
8. CI verde desencadena imágenes ARM64 y bundle ops privado del mismo SHA. First install migra/hardening/seed y deja el admin sólo detrás de TLS local + túnel SSM.
9. Crear founders una vez, confirmar MFA, completar identidad legal y publicar documentos production-ready. Readiness debe pasar antes de habilitar HTTPS público.
10. DNS debe resolver a la EIP antes del arranque público de Caddy. Después ejecutar smoke, IAM/IMDS, backup/restore aislado, segundo deployment y rollback.
