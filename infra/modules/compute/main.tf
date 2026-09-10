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
resource "aws_instance" "pilot" {
  ami                    = var.ami_id
  instance_type          = "t4g.small"
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = var.instance_profile
  monitoring             = true
  ebs_optimized          = true
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1

  }
  user_data                   = file("${path.module}/user-data.sh")
  user_data_replace_on_change = false
  root_block_device {
    encrypted   = true
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
