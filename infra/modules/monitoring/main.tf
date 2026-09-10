variable "name" {
  type = string
}
variable "instance_id" {
  type = string
}
variable "alert_emails" {
  type = list(string)
}
variable "monthly_limit" {
  type    = number
  default = 35
}
resource "aws_sns_topic" "alerts" {
  name = "${var.name}-alerts"
}
resource "aws_sns_topic_subscription" "email" {
  for_each  = toset(var.alert_emails)
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = each.value
}
resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name          = "${var.name}-review-growth-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 70
  alarm_description   = "Revisar activación de Growth; no escala automáticamente."
  alarm_actions       = [aws_sns_topic.alerts.arn]
  dimensions = {
    InstanceId = var.instance_id

  }
}
resource "aws_budgets_budget" "monthly" {
  name         = "${var.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_limit)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  dynamic "notification" {
    for_each = {
      warning_1 = 25, warning_2 = 30, critical_review = 35

    }
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value / var.monthly_limit * 100
      threshold_type             = "PERCENTAGE"
      notification_type          = "FORECASTED"
      subscriber_email_addresses = var.alert_emails

    }

  }
}
