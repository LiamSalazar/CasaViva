# Control de costos

Objetivo Pilot: USD 20–30/mes antes de impuestos/variación; revisar cotización real de `mx-central-1` antes del apply. Los principales costos son t4g.small, EBS 30 GB, IPv4 pública, S3/ECR/CloudWatch y transferencia. El rango puede superar el objetivo por precio regional e IPv4, por lo que el presupuesto manda sobre la estimación.

Budget parametrizable: USD 25 primera advertencia, 30 segunda y 35 revisión crítica. Nunca apaga recursos. Sin NAT, ALB, RDS, CloudFront ni nodos ociosos en Pilot. Revisar Cost Explorer, logs, snapshots, ECR sin tag y versiones S3 cada mes.
