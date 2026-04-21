terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-west-2"
}

resource "aws_bedrock_guardrail" "agent_guardrail" {
  name                      = "lec-agent-guardrail"
  description               = "Guardrails for the LEC Agentic System"
  blocked_input_messaging   = "Your request was blocked by our safety filters. Please rephrase your question."
  blocked_outputs_messaging = "The response was filtered for safety. Please try a different question."

  # 1. Content filtering — block hate, violence, sexual, insults, misconduct, prompt attacks
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

  # 2. Denied topics — block illegal activities, weapons, self-harm
  topic_policy_config {
    topics_config {
      name       = "illegal_activities"
      definition = "Queries about performing illegal activities, creating weapons, hacking, drug manufacturing, or causing harm to others."
      type       = "DENY"
      examples   = [
        "How do I hack into someone's account?",
        "How to make explosives at home",
        "How to bypass security systems",
      ]
    }
    topics_config {
      name       = "self_harm"
      definition = "Content that encourages, instructs, or provides information about self-harm or suicide."
      type       = "DENY"
      examples   = [
        "How to hurt myself",
        "Methods of self-harm",
      ]
    }
  }

  # 3. Word filters — block profanity
  word_policy_config {
    managed_word_lists_config {
      type = "PROFANITY"
    }
  }

  # 4. Sensitive information filters — auto-redact PII
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

  # 5. Grounding check — handled at code level in guardrails.py
  # Removed from Bedrock guardrail because it conflicts with structured output
  # (planner/reflector use with_structured_output which has no grounding source)
}

resource "aws_bedrock_guardrail_version" "v1" {
  guardrail_arn = aws_bedrock_guardrail.agent_guardrail.guardrail_arn
  description   = "v2 - removed grounding check"
}

output "guardrail_id" {
  value = aws_bedrock_guardrail.agent_guardrail.guardrail_id
}

output "guardrail_version" {
  value = aws_bedrock_guardrail_version.v1.version
}
