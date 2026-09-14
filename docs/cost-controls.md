# Control de costos

Objetivo Pilot: aproximadamente USD 21–31/mes antes de impuestos/variación; revisar AWS Pricing Calculator para `mx-central-1` antes de cada apply. Los principales costos son t4g.small, EBS raíz y PostgreSQL, IPv4 pública, S3/ECR/CloudWatch, transferencia y una customer-managed KMS key (aproximadamente USD 1/mes, más solicitudes). El rango puede superar el objetivo por precio regional, IPv4, uso de KMS o tráfico, por lo que el presupuesto manda sobre la estimación.

Budget parametrizable: USD 25 primera advertencia, 30 segunda y 35 revisión crítica. Nunca apaga recursos. Sin NAT, ALB, RDS, CloudFront ni nodos ociosos en Pilot. Revisar Cost Explorer, logs, snapshots, ECR sin tag y versiones S3 cada mes.
