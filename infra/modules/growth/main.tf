variable "enabled" {
  type    = bool
  default = false
}
variable "database_external" {
  type    = bool
  default = false
}
variable "name" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "app_subnet_ids" { type = list(string) }
variable "ami_id" { type = string }
variable "instance_profile" { type = string }
variable "certificate_arn" {
  type    = string
  default = null
}
variable "instance_type" {
  type    = string
  default = "t4g.small"
}
resource "terraform_data" "guard" {
  lifecycle {
    precondition {
      condition     = !var.enabled
      error_message = "Growth is future architecture and is NOT PRODUCTION READY; enabling it is intentionally blocked until its bootstrap and private-network endpoints are completed."
    }
  }
}

resource "aws_security_group" "alb" {
  count  = var.enabled ? 1 : 0
  name   = "${var.name}-growth-alb"
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

resource "aws_security_group" "app" {
  count  = var.enabled ? 1 : 0
  name   = "${var.name}-growth-app"
  vpc_id = var.vpc_id
  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb[0].id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "app" {
  count              = var.enabled ? 1 : 0
  name               = "${var.name}-growth"
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.alb[0].id]
}

resource "aws_lb_target_group" "app" {
  count    = var.enabled ? 1 : 0
  name     = "${var.name}-growth"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  health_check {
    path    = "/api/health/ready/"
    matcher = "200-399"
  }
}

resource "aws_lb_listener" "app" {
  count             = var.enabled ? 1 : 0
  load_balancer_arn = aws_lb.app[0].arn
  port              = var.certificate_arn == null ? 80 : 443
  protocol          = var.certificate_arn == null ? "HTTP" : "HTTPS"
  certificate_arn   = var.certificate_arn
  ssl_policy        = var.certificate_arn == null ? null : "ELBSecurityPolicy-TLS13-1-2-2021-06"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app[0].arn
  }
}

resource "aws_launch_template" "app" {
  count         = var.enabled ? 1 : 0
  name_prefix   = "${var.name}-growth-"
  image_id      = var.ami_id
  instance_type = var.instance_type
  iam_instance_profile { name = var.instance_profile }
  network_interfaces {
    associate_public_ip_address = false
    security_groups             = [aws_security_group.app[0].id]
  }
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }
  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "${var.name}-growth", Stateful = "false" }
  }
}

resource "aws_autoscaling_group" "app" {
  count               = var.enabled ? 1 : 0
  name                = "${var.name}-growth"
  min_size            = 1
  desired_capacity    = 1
  max_size            = 4
  vpc_zone_identifier = var.app_subnet_ids
  target_group_arns   = [aws_lb_target_group.app[0].arn]
  launch_template {
    id      = aws_launch_template.app[0].id
    version = "$Latest"
  }
}

resource "aws_autoscaling_policy" "cpu" {
  count                  = var.enabled ? 1 : 0
  name                   = "${var.name}-growth-cpu"
  autoscaling_group_name = aws_autoscaling_group.app[0].name
  policy_type            = "TargetTrackingScaling"
  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 65
  }
}

output "alb_dns_name" { value = var.enabled ? aws_lb.app[0].dns_name : null }
