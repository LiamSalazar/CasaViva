variable "names" {
  type = set(string)
}
resource "aws_ecr_repository" "this" {
  for_each             = var.names
  name                 = each.value
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true

  }
  encryption_configuration {
    encryption_type = "AES256"

  }
}
resource "aws_ecr_lifecycle_policy" "this" {
  for_each   = aws_ecr_repository.this
  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1, description = "Expire untagged only", selection = {
        tagStatus = "untagged", countType = "sinceImagePushed", countUnit = "days", countNumber = 14

        }, action = {
        type = "expire"

      }

      }, {
      rulePriority = 2, description = "Keep the 30 newest immutable SHA images", selection = {
        tagStatus = "tagged", tagPatternList = ["*"], countType = "imageCountMoreThan", countNumber = 30
      }, action   = { type = "expire" }
    }]

  })
}
output "repository_arns" {
  value = [for item in aws_ecr_repository.this : item.arn]
}
output "repository_urls" { value = { for name, item in aws_ecr_repository.this : name => item.repository_url } }
