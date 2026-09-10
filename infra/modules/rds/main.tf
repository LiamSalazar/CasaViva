variable "enabled" {
  type    = bool
  default = false
}
variable "name" {
  type = string
}
variable "subnet_ids" {
  type = list(string)
}
variable "vpc_security_group_ids" {
  type = list(string)
}
variable "master_username" {
  type    = string
  default = "casaviva_migrator"
}
resource "aws_db_subnet_group" "this" {
  count      = var.enabled ? 1 : 0
  name       = var.name
  subnet_ids = var.subnet_ids
}
resource "aws_db_instance" "this" {
  count                       = var.enabled ? 1 : 0
  identifier                  = var.name
  engine                      = "postgres"
  engine_version              = "18"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  max_allocated_storage       = 100
  storage_encrypted           = true
  multi_az                    = false
  publicly_accessible         = false
  username                    = var.master_username
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.this[0].name
  vpc_security_group_ids      = var.vpc_security_group_ids
  backup_retention_period     = 7
  deletion_protection         = true
  copy_tags_to_snapshot       = true
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${var.name}-final"
  parameter_group_name        = "default.postgres18"
}
