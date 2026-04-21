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

variable "amplify_github_token" {
  description = "GitHub personal access token for Amplify"
  type        = string
  sensitive   = true
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
# 4. Amplify App — hosts the Next.js frontend
# ══════════════════════════════════════════════════════════════════════════

resource "aws_amplify_app" "frontend" {
  name         = "${var.project_name}-frontend"
  repository   = "https://github.com/${var.github_repo}"
  access_token = var.amplify_github_token

  build_spec = <<-EOT
    version: 1
    applications:
      - frontend:
          phases:
            preBuild:
              commands:
                - cd "Agentic System/frontend"
                - npm ci
            build:
              commands:
                - npm run build
          artifacts:
            baseDirectory: "Agentic System/frontend/.next"
            files:
              - '**/*'
          cache:
            paths:
              - "Agentic System/frontend/node_modules/**/*"
        appRoot: "Agentic System/frontend"
  EOT

  environment_variables = {
    NEXT_PUBLIC_API_URL = "https://api.placeholder.com" # Updated after AgentCore Runtime deploy
  }
}

resource "aws_amplify_branch" "main" {
  app_id      = aws_amplify_app.frontend.id
  branch_name = "main"
  stage       = "PRODUCTION"
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
          "iam:PassRole",
          "s3:*",
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

output "amplify_app_id" {
  value = aws_amplify_app.frontend.id
}

output "amplify_default_domain" {
  value = aws_amplify_app.frontend.default_domain
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "agentcore_runtime_role_arn" {
  value = aws_iam_role.agentcore_runtime.arn
}
