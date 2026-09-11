# Política de escaneo de seguridad

CI ejecuta `npm audit`, `pip-audit`, Trivy para filesystem/imágenes, Checkov y tflint. Secret scan busca claves AWS, tokens GitHub y claves privadas versionadas. HIGH/CRITICAL explotables o con corrección disponible bloquean la entrega. Una excepción por falso positivo o ausencia real de fix debe documentar identificador, componente alcanzable, mitigación, responsable y fecha de revisión; bajar severidad sin análisis no está permitido.

GitHub publica mediante OIDC; EC2 usa Instance Profile e IMDSv2 required con hop limit 2 para Docker. No se aceptan access keys estáticas. El frontend nunca recibe credenciales. S3 mantiene Block Public Access, cifrado y versioning.
