variable "name" {
  type = string
}
variable "vpc_id" {
  type = string
}
variable "subnet_id" {
  type = string
}
variable "instance_profile" {
  type = string
}
variable "ami_id" {
  type = string
}
variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key used exclusively for Pilot EBS encryption."
}
variable "postgres_volume_size" {
  type    = number
  default = 20
  validation {
    condition     = var.postgres_volume_size >= 20
    error_message = "PostgreSQL data volume must be at least 20 GiB."
  }
}
resource "aws_security_group" "app" {
  name   = "${var.name}-web"
  vpc_id = var.vpc_id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]

  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]

  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]

  }
}
data "aws_subnet" "selected" { id = var.subnet_id }
resource "aws_instance" "pilot" {
  # checkov:skip=CKV_AWS_126:Pilot uses basic EC2 monitoring plus selective CloudWatch Agent metrics for cost control; Growth must reevaluate detailed monitoring.
  ami                    = var.ami_id
  instance_type          = "t4g.small"
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = var.instance_profile
  monitoring             = false
  ebs_optimized          = true
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2

  }
  user_data = templatefile("${path.module}/user-data.sh", {
    postgres_volume_id = aws_ebs_volume.postgres.id
    deploy_script      = base64encode(file("${path.root}/../../../scripts/deploy-pilot.sh"))
    rollback_script    = base64encode(file("${path.root}/../../../scripts/rollback-pilot.sh"))
    backup_script      = base64encode(file("${path.root}/../../../scripts/backup-postgres-s3.sh"))
    compose_file       = base64encode(file("${path.root}/../../../docker-compose.production.yml"))
    caddy_file         = base64encode(file("${path.root}/../../../docker/Caddyfile"))
    init_roles         = base64encode(file("${path.root}/../../../docker/postgres/init-roles.sh"))
    cloudwatch_config  = base64encode(file("${path.root}/../../../docker/cloudwatch-agent.json"))
  })
  user_data_replace_on_change = false
  root_block_device {
    encrypted   = true
    kms_key_id  = var.kms_key_arn
    volume_type = "gp3"
    volume_size = 30

  }
  tags = {
    Name = var.name, Stateful = "true", Replacement = "manual-only"

  }
  lifecycle {
    prevent_destroy = true

  }
}
resource "aws_ebs_volume" "postgres" {
  availability_zone = data.aws_subnet.selected.availability_zone
  encrypted         = true
  kms_key_id        = var.kms_key_arn
  type              = "gp3"
  size              = var.postgres_volume_size
  tags = {
    Name      = "${var.name}-postgres-data"
    Stateful  = "true"
    Retention = "retain-on-instance-replacement"
  }
  lifecycle { prevent_destroy = true }
}
resource "aws_volume_attachment" "postgres" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.postgres.id
  instance_id = aws_instance.pilot.id
}
resource "aws_eip" "pilot" {
  domain   = "vpc"
  instance = aws_instance.pilot.id
}
output "instance_id" {
  value = aws_instance.pilot.id
}
output "public_ip" {
  value = aws_eip.pilot.public_ip
}
output "postgres_volume_id" { value = aws_ebs_volume.postgres.id }
