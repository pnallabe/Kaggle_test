variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "GCP region"
}

variable "app_name" {
  type        = string
  default     = "ai-data-analyst"
  description = "Application name"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment (dev, staging, prod)"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "db_machine_type" {
  type        = string
  default     = "db-f1-micro"
  description = "Cloud SQL machine type"
}

variable "notification_channels" {
  type        = list(string)
  default     = []
  description = "Notification channel IDs for monitoring alerts"
}
