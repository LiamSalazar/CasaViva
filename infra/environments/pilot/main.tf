terraform {
  required_version = ">= 1.13.0, < 2.0.0"
  required_providers {
    aws = {
      source = "hashicorp/aws", version = "~> 6.0"
    }
  }
  backend "s3" {
    use_lockfile = true
    encrypt      = true
  }
}
provider "aws" {
  region = "mx-central-1"
  default_tags {
    tags = {
      Project = "CasaViva", Environment = "pilot", ManagedBy = "Terraform"
    }
  }
}
variable "ami_id" {
  type        = string
  description = "Amazon Linux 2023 ARM64 AMI verified in mx-central-1"
}
variable "alert_emails" {
  type = list(string)
}
variable "bucket_namespace" {
  type = string
}
data "aws_caller_identity" "current" {}
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}
resource "aws_iam_role" "github_deploy" {
  name               = "casaviva-github-deploy"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Federated = aws_iam_openid_connect_provider.github.arn }, Action = "sts:AssumeRoleWithWebIdentity", Condition = { StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }, StringLike = { "token.actions.githubusercontent.com:sub" = ["repo:LiamSalazar/CasaViva:ref:refs/heads/main", "repo:LiamSalazar/CasaViva:environment:production"] } } }] })
}
resource "aws_iam_role_policy" "github_deploy" {
  role   = aws_iam_role.github_deploy.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" }, { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:CompleteLayerUpload", "ecr:GetDownloadUrlForLayer", "ecr:InitiateLayerUpload", "ecr:PutImage", "ecr:UploadLayerPart"], Resource = module.ecr.repository_arns }, { Effect = "Allow", Action = ["ssm:SendCommand"], Resource = ["arn:aws:ssm:mx-central-1::document/AWS-RunShellScript", "arn:aws:ec2:mx-central-1:${data.aws_caller_identity.current.account_id}:instance/${module.compute.instance_id}"] }, { Effect = "Allow", Action = ["ssm:GetCommandInvocation"], Resource = "*" }] })
}
variable "availability_zones" {
  type = list(string)
  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "Provide two supported AZs."
  }
}
locals {
  name = "casaviva-pilot"
}
module "network" {
  source = "../../modules/network"
  name   = local.name
  azs    = var.availability_zones
}
module "ecr" {
  source = "../../modules/ecr"
  names  = ["casaviva-frontend", "casaviva-backend"]
}
module "media" {
  source = "../../modules/media"
  name   = var.bucket_namespace
}
module "iam" {
  source          = "../../modules/iam"
  name            = local.name
  bucket_arns     = [module.media.media_arn, module.media.backup_arn]
  repository_arns = module.ecr.repository_arns
}
module "compute" {
  source           = "../../modules/compute"
  name             = local.name
  vpc_id           = module.network.vpc_id
  subnet_id        = module.network.public_subnet_ids[0]
  instance_profile = module.iam.instance_profile_name
  ami_id           = var.ami_id
}
module "monitoring" {
  source       = "../../modules/monitoring"
  name         = local.name
  instance_id  = module.compute.instance_id
  alert_emails = var.alert_emails
}
output "instance_id" {
  value = module.compute.instance_id
}
output "public_ip" {
  value = module.compute.public_ip
}
