terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "lec-agent-tfstate"
    key    = "agentic-system/terraform.tfstate"
    region = "us-west-2"
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-west-2"
}

variable "project_name" {
  default = "lec-agent"
}

variable "github_repo" {
  default = "pallasaisrujan28/LEC_ASSIGNMENT"
}

# ══════════════════════════════════════════════════════════════════════════
# 1. ECR Repository — stores the backend Docker image
# ══════════════════════════════════════════════════════════════════════════

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ══════════════════════════════════════════════════════════════════════════
# 2. Bedrock Guardrail
# ══════════════════════════════════════════════════════════════════════════

resource "aws_bedrock_guardrail" "agent_guardrail" {
  name                      = "${var.project_name}-guardrail-v2"
  description               = "Guardrails for the LEC Agentic System"
  blocked_input_messaging   = "Your request was blocked by our safety filters. Please rephrase your question."
  blocked_outputs_messaging = "The response was filtered for safety. Please try a different question."

  content_policy_config {
    filters_config {
      type            = "HATE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "INSULTS"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "SEXUAL"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "VIOLENCE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "MISCONDUCT"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
  }

  topic_policy_config {
    topics_config {
      name       = "illegal_activities"
      definition = "Queries about performing illegal activities, creating weapons, hacking, or causing harm."
      type       = "DENY"
      examples   = ["How do I hack into someone's account?", "How to make explosives"]
    }
    topics_config {
      name       = "self_harm"
      definition = "Content that encourages self-harm or suicide."
      type       = "DENY"
      examples   = ["How to hurt myself"]
    }
  }

  word_policy_config {
    managed_word_lists_config {
      type = "PROFANITY"
    }
  }

  sensitive_information_policy_config {
    pii_entities_config {
      type   = "EMAIL"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "PHONE"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "CREDIT_DEBIT_CARD_NUMBER"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "US_SOCIAL_SECURITY_NUMBER"
      action = "BLOCK"
    }
  }
}

resource "aws_bedrock_guardrail_version" "current" {
  guardrail_arn = aws_bedrock_guardrail.agent_guardrail.guardrail_arn
  description   = "current"
}


# ══════════════════════════════════════════════════════════════════════════
# 3. AgentCore Memory (via CloudFormation — no native terraform resource yet)
# ══════════════════════════════════════════════════════════════════════════

resource "aws_cloudformation_stack" "agentcore_memory" {
  name = "${var.project_name}-memory"

  template_body = jsonencode({
    AWSTemplateFormatVersion = "2010-09-09"
    Resources = {
      AgentMemory = {
        Type = "AWS::BedrockAgentCore::Memory"
        Properties = {
          Name                = "lec_agent_memory"
          Description         = "Conversation memory for the LEC agent"
          EventExpiryDuration = 30
          MemoryStrategies = [
            {
              SummaryMemoryStrategy = {
                Name               = "SessionSummarizer"
                NamespaceTemplates = ["/summaries/{actorId}/{sessionId}/"]
              }
            }
          ]
        }
      }
    }
    Outputs = {
      MemoryId = {
        Value = { "Ref" = "AgentMemory" }
      }
    }
  })
}

# ══════════════════════════════════════════════════════════════════════════
# 4. S3 + CloudFront — hosts the Next.js static frontend
# ══════════════════════════════════════════════════════════════════════════

resource "aws_s3_bucket" "frontend" {
  bucket        = "${var.project_name}-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  depends_on = [aws_s3_bucket_public_access_block.frontend]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "CloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
          }
        }
      }
    ]
  })
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${var.project_name}-frontend-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

# ══════════════════════════════════════════════════════════════════════════
# 5. IAM Role — for GitHub Actions OIDC deployments
# ══════════════════════════════════════════════════════════════════════════

data "aws_caller_identity" "current" {}

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_role" "github_actions" {
  name = "${var.project_name}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = data.aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "github_actions_policy" {
  name = "${var.project_name}-deploy-policy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:*",
          "bedrock:*",
          "bedrock-agentcore:*",
          "amplify:*",
          "cloudformation:*",
          "iam:*",
          "s3:*",
          "sts:GetCallerIdentity",
        ]
        Resource = "*"
      }
    ]
  })
}


# ══════════════════════════════════════════════════════════════════════════
# 6. IAM Role for AgentCore Runtime — allows the agent to call Bedrock
# ══════════════════════════════════════════════════════════════════════════

resource "aws_iam_role" "agentcore_runtime" {
  name = "${var.project_name}-agentcore-runtime"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock-agentcore.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "agentcore_runtime_policy" {
  name = "${var.project_name}-agentcore-runtime-policy"
  role = aws_iam_role.agentcore_runtime.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock-agentcore:*",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "*"
      }
    ]
  })
}

# ══════════════════════════════════════════════════════════════════════════
# Outputs
# ══════════════════════════════════════════════════════════════════════════

output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "guardrail_id" {
  value = aws_bedrock_guardrail.agent_guardrail.guardrail_id
}

output "guardrail_version" {
  value = aws_bedrock_guardrail_version.current.version
}

output "agentcore_memory_id" {
  value = aws_cloudformation_stack.agentcore_memory.outputs["MemoryId"]
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.bucket
}

output "frontend_url" {
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.frontend.id
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "agentcore_runtime_role_arn" {
  value = aws_iam_role.agentcore_runtime.arn
}
