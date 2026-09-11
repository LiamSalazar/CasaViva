# Arquitectura AWS Pilot

Región `mx-central-1`; dos subredes públicas y dos privadas en dos AZ soportadas, sin NAT Gateway. Una EC2 `t4g.small` ARM64 con root EBS gp3 cifrado de 30 GB y un EBS gp3 cifrado separado para PostgreSQL ejecuta Caddy, Next, Django y PostgreSQL 18 en Docker. El volumen de datos se conserva ante reemplazo de instancia. La instancia stateful tiene `prevent_destroy`, no ASG y no ofrece HA. Sólo 80/443 son públicos; SSM sustituye SSH.

Media y backups usan buckets privados separados, cifrados, versionados y con Block Public Access. La app usa el IAM role/provider chain. CloudFront+OAC se posterga en Pilot por complejidad para <=500 visitantes/mes. ECR mantiene frontend/backend y elimina sólo imágenes sin tag. Parameter Store Standard/SecureString contiene configuración; secretos no entran en Terraform.

Riesgo aceptado: aplicación y DB comparten host. Objetivos operativos iniciales, no garantía, RPO 24 h y RTO 4 h tras ensayar restauración.
