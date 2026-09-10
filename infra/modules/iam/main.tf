variable "name" {
  type = string
}
variable "bucket_arns" {
  type = list(string)
}
variable "repository_arns" {
  type = list(string)
}
resource "aws_iam_role" "ec2" {
  name = "${var.name}-ec2"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Principal = {
        Service = "ec2.amazonaws.com"

      }, Action = "sts:AssumeRole"

    }]

  })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "app" {
  role = aws_iam_role.ec2.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"], Resource = concat(var.bucket_arns, [for arn in var.bucket_arns : "${arn}/*"])

      }, {
      Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*"

      }, {
      Effect = "Allow", Action = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"], Resource = var.repository_arns

      }, {
      Effect = "Allow", Action = ["ssm:GetParameter", "ssm:GetParametersByPath"], Resource = "arn:aws:ssm:*:*:parameter/${var.name}/*"

      }, {
      Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "arn:aws:logs:*:*:log-group:/casaviva/*"

    }]

  })
}
resource "aws_iam_instance_profile" "this" {
  name = var.name
  role = aws_iam_role.ec2.name
}
output "instance_profile_name" {
  value = aws_iam_instance_profile.this.name
}
