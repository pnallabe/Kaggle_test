terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    # Configure during init: terraform init -backend-config="bucket=YOUR_BUCKET"
    prefix = "ai-data-analyst"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "cloudsql.googleapis.com",
    "storage.googleapis.com",
    "bigquery.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "cloudkms.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "identitytoolkit.googleapis.com",
    "cloudidentity.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "aiplatform.googleapis.com"
  ])

  service = each.value
  disable_on_destroy = false
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${var.app_name}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.app_name}-subnet"
  ip_cidr_range = "10.0.0.0/16"
  region        = var.region
  network       = google_compute_network.vpc.id

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Firewall - allow internal traffic
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.app_name}-allow-internal"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  source_ranges = ["10.0.0.0/16"]
}

# Cloud Armor Security Policy (for API Gateway)
resource "google_compute_security_policy" "cloud_armor" {
  name = "${var.app_name}-security-policy"

  rules {
    action   = "allow"
    priority = "1000"
    match {
      versioned_expr = "EXPR_V1"
      expr {
        expression = "origin.region_code == 'US' || origin.region_code == 'CA'"
      }
    }
    description = "Allow traffic from US and CA"
  }

  rules {
    action   = "deny(403)"
    priority = "2000"
    match {
      versioned_expr = "EXPR_V1"
      expr {
        expression = "evaluatePreconfiguredExpr('xss-v33')"
      }
    }
    description = "Deny XSS"
  }

  rules {
    action   = "allow"
    priority = "65535"
    match {
      versioned_expr = "EXPR_V1"
      expr {
        expression = "true"
      }
    }
    description = "Default rule"
  }
}

# GCS bucket for artifacts and UI
resource "google_storage_bucket" "artifacts" {
  name          = "${var.project_id}-artifacts-${random_string.bucket_suffix.result}"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  cors {
    origin          = ["https://*.example.com"]
    method          = ["GET", "HEAD", "PUT", "POST"]
    response_header = ["Content-Type", "x-goog-meta-*"]
    max_age_seconds = 3600
  }
}

# GCS bucket for backend code and configurations
resource "google_storage_bucket" "backend_storage" {
  name          = "${var.project_id}-backend-${random_string.bucket_suffix.result}"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

# Random suffix for globally unique bucket names
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  lower   = true
}

# Cloud SQL PostgreSQL instance
resource "google_sql_database_instance" "metadata_db" {
  name             = "${var.app_name}-postgres-${random_string.db_suffix.result}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier            = var.db_machine_type
    availability_type = "REGIONAL"
    disk_size       = 20
    disk_type       = "PD_SSD"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      require_ssl    = true
      ipv4_enabled   = false
      private_network = google_compute_network.vpc.id

      authorized_networks {
        name  = "allow-cloud-run"
        value = "0.0.0.0/0" # Cloud Run uses dynamic IPs; use private IP in production
      }
    }

    database_flags {
      name  = "cloudsql_iam_authentication"
      value = "on"
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
    }
  }

  deletion_protection = true
}

resource "random_string" "db_suffix" {
  length  = 4
  special = false
  lower   = true
}

# Cloud SQL database
resource "google_sql_database" "metadata" {
  name     = "ai_analyst"
  instance = google_sql_database_instance.metadata_db.name
}

# Cloud SQL root user password
resource "random_password" "db_root_password" {
  length  = 32
  special = true
}

resource "google_sql_user" "root" {
  name     = "postgres"
  instance = google_sql_database_instance.metadata_db.name
  password = random_password.db_root_password.result
}

# Cloud SQL API user (for application)
resource "google_sql_user" "api_user" {
  name     = "api_service"
  instance = google_sql_database_instance.metadata_db.name
  password = random_password.api_password.result
  type     = "BUILT_IN"
}

resource "random_password" "api_password" {
  length  = 32
  special = true
}

# Secret Manager secrets for database credentials
resource "google_secret_manager_secret" "db_connection_string" {
  secret_id = "${var.app_name}-db-connection-string"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_connection_string" {
  secret      = google_secret_manager_secret.db_connection_string.id
  secret_data = "postgresql://${google_sql_user.api_user.name}:${google_sql_user.api_user.password}@${google_sql_database_instance.metadata_db.private_ip_address}:5432/${google_sql_database.metadata.name}"
}

# BigQuery dataset
resource "google_bigquery_dataset" "analytics" {
  dataset_id    = "analytics_${replace(var.app_name, "-", "_")}"
  friendly_name = "AI Data Analyst Analytics"
  description   = "Primary analytics dataset for AI Data Analyst"
  location      = var.region

  default_table_expiration_ms = null
  default_partition_expiration_ms = null

  access {
    role          = "OWNER"
    user_by_email = google_service_account.api.email
  }
}

# BigQuery audit dataset
resource "google_bigquery_dataset" "audit" {
  dataset_id    = "audit_${replace(var.app_name, "-", "_")}"
  friendly_name = "Audit Logs"
  description   = "Audit logs for AI Data Analyst"
  location      = var.region

  default_table_expiration_ms = 7776000000 # 90 days in milliseconds

  access {
    role          = "OWNER"
    user_by_email = google_service_account.api.email
  }
}

# Pub/Sub topic for job queue
resource "google_pubsub_topic" "job_queue" {
  name                       = "${var.app_name}-jobs"
  message_retention_duration = "86400s" # 24 hours
}

# Pub/Sub subscription for workers
resource "google_pubsub_subscription" "job_subscription" {
  name             = "${var.app_name}-jobs-subscription"
  topic            = google_pubsub_topic.job_queue.name
  ack_deadline_seconds = 60

  push_config {
    push_endpoint = google_cloud_run_service.api.status[0].url
  }
}

# Service account for API
resource "google_service_account" "api" {
  account_id   = "${var.app_name}-api"
  display_name = "API Service Account"
}

# Service account for Cloud Run workers
resource "google_service_account" "worker" {
  account_id   = "${var.app_name}-worker"
  display_name = "Worker Service Account"
}

# IAM roles for API service account
resource "google_project_iam_member" "api_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.editor"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_gcs" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# IAM roles for Worker service account
resource "google_project_iam_member" "worker_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "worker_gcs" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "worker_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "worker_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

# Placeholder for Cloud Run service (will be deployed via CI/CD)
resource "google_cloud_run_service" "api" {
  name     = var.app_name
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.api.email

      containers {
        image = "gcr.io/cloud-builders/gke-deploy" # Placeholder; replaced by CI/CD
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_project_service.required_apis["run.googleapis.com"]]
}

resource "google_cloud_run_service_iam_member" "public_access" {
  service       = google_cloud_run_service.api.name
  location      = google_cloud_run_service.api.location
  role          = "roles/run.invoker"
  member        = "allUsers"
}

# Cloud KMS key ring for encryption
resource "google_kms_key_ring" "keyring" {
  name       = "${var.app_name}-keyring"
  location   = var.region
}

# Cloud KMS crypto key
resource "google_kms_crypto_key" "key" {
  name            = "${var.app_name}-key"
  key_ring        = google_kms_key_ring.keyring.id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

# Memorystore Redis for caching
resource "google_redis_instance" "cache" {
  name           = "${var.app_name}-cache"
  tier           = "standard"
  memory_size_gb = 1
  region         = var.region

  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version       = "7.0"
  display_name        = "AI Analyst Cache"
  auth_enabled        = true
  reserved_ip_range   = "10.1.0.0/29"

  depends_on = [google_compute_network.vpc]
}

# Cloud Logging sink for audit logs
resource "google_logging_project_sink" "audit_sink" {
  name        = "${var.app_name}-audit-sink"
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.audit.dataset_id}"

  filter = <<-EOT
    protoPayload.serviceName="cloudsql.googleapis.com"
    OR protoPayload.serviceName="storage.googleapis.com"
    OR protoPayload.serviceName="bigquery.googleapis.com"
  EOT

  unique_writer_identity = true
}

# Grant the logging sink write permissions
resource "google_bigquery_dataset_iam_member" "audit_logging" {
  dataset_id = google_bigquery_dataset.audit.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.audit_sink.writer_identity
}

# Cloud Monitoring alert policy for high error rates
resource "google_monitoring_alert_policy" "cloud_run_errors" {
  display_name = "${var.app_name} - High Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run Error Rate > 1%"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.app_name}\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.01
      aggregations {
        alignment_period  = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.notification_channels
}
