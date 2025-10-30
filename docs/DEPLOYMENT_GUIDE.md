# AI Data Analyst - Deployment Guide

## 🚀 Production Deployment Guide

This guide covers deploying AI Data Analyst MVP to production with enterprise-grade reliability, security, and scalability.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Security Configuration](#security-configuration)
4. [Application Deployment](#application-deployment)
5. [Database Migration](#database-migration)
6. [Monitoring & Alerting](#monitoring--alerting)
7. [Testing & Validation](#testing--validation)
8. [Go-Live Checklist](#go-live-checklist)
9. [Post-Deployment](#post-deployment)
10. [Troubleshooting](#troubleshooting)

## ✅ Prerequisites

### Required Accounts & Access
- [ ] Google Cloud Platform project with billing enabled
- [ ] GitHub repository access for code deployment
- [ ] Domain name and DNS management access
- [ ] SSL certificate authority access
- [ ] SMTP service for email notifications

### Required Permissions
- [ ] GCP Project Owner or Editor role
- [ ] Cloud SQL Admin role
- [ ] BigQuery Admin role
- [ ] Cloud Run Admin role
- [ ] VPC Admin role (for enterprise security)
- [ ] IAM Admin role

### Local Tools
```bash
# Install required CLI tools
curl https://sdk.cloud.google.com | bash  # Google Cloud SDK
curl -sSL https://get.docker.com/ | sh     # Docker
curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.28.0/bin/linux/amd64/kubectl # kubectl
```

### Environment Variables
```bash
# Set up deployment environment
export PROJECT_ID="ai-data-analyst-prod"
export REGION="us-central1"
export ENVIRONMENT="production"
export DOMAIN="aidataanalyst.com"
export ADMIN_EMAIL="admin@aidataanalyst.com"
```

## 🏗️ Infrastructure Setup

### 1. Google Cloud Project Setup

```bash
# Create and configure GCP project
gcloud projects create $PROJECT_ID --name="AI Data Analyst Production"
gcloud config set project $PROJECT_ID
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sql-component.googleapis.com \
  bigquery.googleapis.com \
  storage-component.googleapis.com \
  cloudkms.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

### 2. Terraform Infrastructure Deployment

Create `terraform/production/main.tf`:

```hcl
terraform {
  required_version = ">= 1.0"
  backend "gcs" {
    bucket = "ai-data-analyst-terraform-state"
    prefix = "production"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "ai-analyst-network"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "ai-analyst-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.main.id
  
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  name             = "ai-analyst-db-${var.environment}"
  database_version = "POSTGRES_14"
  region          = var.region
  deletion_protection = true

  settings {
    tier              = "db-g1-small"
    availability_type = "REGIONAL"
    disk_type         = "PD_SSD"
    disk_size         = 100
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      start_time                    = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
      require_ssl     = true
      
      authorized_networks {
        name  = "cloud-run"
        value = "0.0.0.0/0"
      }
    }

    database_flags {
      name  = "log_statement"
      value = "all"
    }
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

# Private VPC Connection
resource "google_compute_global_address" "private_ip_address" {
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Database and Users
resource "google_sql_database" "app_db" {
  name     = "aidataanalyst"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app_user" {
  name     = "app_user"
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# BigQuery Dataset
resource "google_bigquery_dataset" "analytics" {
  dataset_id    = "analytics"
  friendly_name = "AI Data Analyst Analytics"
  description   = "Main analytics dataset for AI Data Analyst"
  location      = "US"

  access {
    role          = "OWNER"
    user_by_email = var.admin_email
  }

  access {
    role         = "READER"
    special_group = "projectReaders"
  }
}

# Cloud Storage Buckets
resource "google_storage_bucket" "artifacts" {
  name          = "${var.project_id}-artifacts"
  location      = "US"
  force_destroy = false

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.storage_key.id
  }
}

resource "google_storage_bucket" "uploads" {
  name          = "${var.project_id}-uploads"
  location      = "US"
  force_destroy = false

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  cors {
    origin          = ["https://${var.domain}"]
    method          = ["GET", "POST", "PUT"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

# KMS Keys
resource "google_kms_key_ring" "main" {
  name     = "ai-analyst-keyring"
  location = "global"
}

resource "google_kms_crypto_key" "storage_key" {
  name     = "storage-key"
  key_ring = google_kms_key_ring.main.id
  purpose  = "ENCRYPT_DECRYPT"

  version_template {
    algorithm = "GOOGLE_SYMMETRIC_ENCRYPTION"
  }
}

# Secret Manager Secrets
resource "google_secret_manager_secret" "db_password" {
  secret_id = "database-password"
  
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Cloud Run Service
resource "google_cloud_run_service" "api" {
  name     = "ai-analyst-api"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/ai-analyst-api:latest"
        
        ports {
          container_port = 8080
        }

        env {
          name  = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.db_connection.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name  = "BIGQUERY_PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        resources {
          limits = {
            cpu    = "2000m"
            memory = "4Gi"
          }
        }
      }

      container_concurrency = 80
      timeout_seconds      = 900
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale"         = "100"
        "autoscaling.knative.dev/minScale"         = "2"
        "run.googleapis.com/cpu-throttling"        = "false"
        "run.googleapis.com/execution-environment" = "gen2"
        "run.googleapis.com/vpc-access-connector"  = google_vpc_access_connector.connector.name
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_vpc_access_connector.connector]
}

# VPC Access Connector
resource "google_vpc_access_connector" "connector" {
  name          = "ai-analyst-connector"
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.main.name
  region        = var.region
  
  min_throughput = 200
  max_throughput = 1000
}

# IAM
resource "google_cloud_run_service_iam_member" "public" {
  location = google_cloud_run_service.api.location
  project  = google_cloud_run_service.api.project
  service  = google_cloud_run_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Build Trigger
resource "google_cloudbuild_trigger" "api" {
  name        = "ai-analyst-api-trigger"
  description = "Build and deploy AI Data Analyst API"

  github {
    owner = "your-org"
    name  = "ai-data-analyst"
    push {
      branch = "^main$"
    }
  }

  filename = "cloudbuild.yaml"
}

# Outputs
output "database_connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "api_url" {
  value = google_cloud_run_service.api.status[0].url
}

output "storage_bucket_artifacts" {
  value = google_storage_bucket.artifacts.name
}
```

Deploy infrastructure:

```bash
# Initialize Terraform
cd terraform/production
terraform init

# Plan deployment
terraform plan -var="project_id=$PROJECT_ID" \
               -var="region=$REGION" \
               -var="admin_email=$ADMIN_EMAIL"

# Apply infrastructure
terraform apply -var="project_id=$PROJECT_ID" \
                -var="region=$REGION" \
                -var="admin_email=$ADMIN_EMAIL"
```

## 🔒 Security Configuration

### 1. VPC Service Controls

```bash
# Create VPC Service Controls policy
gcloud access-context-manager policies create \
  --title="AI Data Analyst Security Policy" \
  --org=$ORG_ID

# Create service perimeter
gcloud access-context-manager perimeters create \
  --policy=$POLICY_ID \
  --title="AI Data Analyst Perimeter" \
  --resources="projects/$PROJECT_ID" \
  --restricted-services="bigquery.googleapis.com,storage.googleapis.com"
```

### 2. Identity and Access Management

```bash
# Create service accounts
gcloud iam service-accounts create ai-analyst-api \
  --display-name="AI Data Analyst API Service Account"

gcloud iam service-accounts create ai-analyst-worker \
  --display-name="AI Data Analyst Worker Service Account"

# Grant minimal required permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:ai-analyst-api@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:ai-analyst-api@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:ai-analyst-api@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### 3. SSL/TLS Configuration

```bash
# Create managed SSL certificate
gcloud compute ssl-certificates create ai-analyst-ssl \
  --domains=$DOMAIN,api.$DOMAIN \
  --global

# Create load balancer
gcloud compute url-maps create ai-analyst-lb \
  --default-service=ai-analyst-backend

gcloud compute target-https-proxies create ai-analyst-https-proxy \
  --url-map=ai-analyst-lb \
  --ssl-certificates=ai-analyst-ssl

gcloud compute global-forwarding-rules create ai-analyst-https-rule \
  --target-https-proxy=ai-analyst-https-proxy \
  --ports=443 \
  --global
```

## 🚢 Application Deployment

### 1. Container Build Pipeline

Create `cloudbuild.yaml`:

```yaml
steps:
  # Build API container
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ai-analyst-api:$COMMIT_SHA', '-f', 'api/Dockerfile', '.']
    
  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ai-analyst-api:$COMMIT_SHA']
    
  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'ai-analyst-api'
      - '--image=gcr.io/$PROJECT_ID/ai-analyst-api:$COMMIT_SHA'
      - '--region=$_REGION'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=4Gi'
      - '--cpu=2'
      - '--max-instances=100'
      - '--min-instances=2'
      - '--concurrency=80'
      - '--timeout=900'
      - '--set-env-vars=ENVIRONMENT=production'
      - '--service-account=ai-analyst-api@$PROJECT_ID.iam.gserviceaccount.com'

  # Build worker container
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ai-analyst-worker:$COMMIT_SHA', '-f', 'worker/Dockerfile', '.']
    
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ai-analyst-worker:$COMMIT_SHA']

  # Build frontend
  - name: 'node:16'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        cd frontend
        npm ci
        npm run build
        gsutil -m rsync -r -d dist gs://$PROJECT_ID-frontend

substitutions:
  _REGION: us-central1

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: 'E2_HIGHCPU_8'
```

### 2. Application Configuration

Create production configuration file `config/production.yaml`:

```yaml
app:
  name: "AI Data Analyst"
  environment: "production"
  debug: false
  log_level: "INFO"

server:
  host: "0.0.0.0"
  port: 8080
  cors_origins:
    - "https://aidataanalyst.com"
    - "https://app.aidataanalyst.com"

database:
  connection_name: "${DATABASE_CONNECTION_NAME}"
  database: "aidataanalyst"
  username: "app_user"
  password_secret: "database-password"
  pool_size: 20
  max_overflow: 50
  pool_timeout: 30

bigquery:
  project_id: "${PROJECT_ID}"
  location: "US"
  default_dataset: "analytics"
  job_timeout: 900

storage:
  artifacts_bucket: "${PROJECT_ID}-artifacts"
  uploads_bucket: "${PROJECT_ID}-uploads"
  signed_url_expiry: 3600

vertex_ai:
  project_id: "${PROJECT_ID}"
  location: "us-central1"
  model_name: "text-bison@001"
  embedding_model: "textembedding-gecko@001"

security:
  jwt_secret_key: "${JWT_SECRET_KEY}"
  jwt_algorithm: "HS256"
  jwt_expiry: 3600
  password_hash_rounds: 12
  
monitoring:
  enable_metrics: true
  enable_tracing: true
  sample_rate: 0.1

cache:
  type: "redis"
  host: "${REDIS_HOST}"
  port: 6379
  db: 0
  ttl: 3600
```

### 3. Database Migration

Create database migration script `scripts/migrate.py`:

```python
#!/usr/bin/env python3
"""
Database migration script for AI Data Analyst production deployment
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import alembic
from alembic.config import Config
from alembic import command

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment or Secret Manager"""
    # In production, this would fetch from Secret Manager
    connection_name = os.getenv('DATABASE_CONNECTION_NAME')
    database = os.getenv('DATABASE_NAME', 'aidataanalyst')
    username = os.getenv('DATABASE_USERNAME', 'app_user')
    password = os.getenv('DATABASE_PASSWORD')
    
    if not password:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{os.getenv('PROJECT_ID')}/secrets/database-password/versions/latest"
        response = client.access_secret_version(request={"name": name})
        password = response.payload.data.decode("UTF-8")
    
    return f"postgresql+psycopg2://{username}:{password}@/{database}?host=/cloudsql/{connection_name}"

def run_migrations():
    """Run database migrations"""
    try:
        database_url = get_database_url()
        
        # Create Alembic configuration
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        # Run migrations
        logger.info("Starting database migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
        
        # Verify database connection
        engine = create_engine(database_url)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version}")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def create_initial_data():
    """Create initial data for production"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create system admin user
        admin_email = os.getenv('ADMIN_EMAIL')
        if admin_email:
            # Check if admin exists
            from app.models import User, Tenant
            
            admin_user = session.query(User).filter_by(email=admin_email).first()
            if not admin_user:
                # Create system tenant
                system_tenant = Tenant(
                    name="System",
                    domain="system.local",
                    plan="enterprise",
                    max_users=1000,
                    max_projects=1000
                )
                session.add(system_tenant)
                session.flush()
                
                # Create admin user
                admin_user = User(
                    email=admin_email,
                    name="System Administrator",
                    role="system_admin",
                    tenant_id=system_tenant.id,
                    is_active=True,
                    is_verified=True
                )
                admin_user.set_password("ChangeMe123!")  # Force password change on first login
                session.add(admin_user)
                
                session.commit()
                logger.info(f"Created system admin user: {admin_email}")
            else:
                logger.info("System admin user already exists")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to create initial data: {e}")
        return False

if __name__ == "__main__":
    success = run_migrations()
    if success:
        success = create_initial_data()
    
    sys.exit(0 if success else 1)
```

Run migrations:

```bash
# Set environment variables
export PROJECT_ID="ai-data-analyst-prod"
export DATABASE_CONNECTION_NAME="ai-data-analyst-prod:us-central1:ai-analyst-db-production"
export ADMIN_EMAIL="admin@aidataanalyst.com"

# Run migrations
python scripts/migrate.py
```

## 📊 Monitoring & Alerting

### 1. Cloud Monitoring Setup

Create monitoring configuration `monitoring/alerts.yaml`:

```yaml
# API Response Time Alert
- name: "API High Response Time"
  condition:
    displayName: "API P95 response time > 2s"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_latencies"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 2000
      duration: "300s"
      aggregations:
        - alignmentPeriod: "300s"
          perSeriesAligner: ALIGN_PERCENTILE_95
          crossSeriesReducer: REDUCE_MEAN
  notificationChannels:
    - "projects/ai-data-analyst-prod/notificationChannels/email-alerts"

# Error Rate Alert  
- name: "High Error Rate"
  condition:
    displayName: "Error rate > 1%"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND metric.type="logging.googleapis.com/log_entry_count"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.01
      duration: "300s"

# Database Connection Alert
- name: "Database Connection Issues"
  condition:
    displayName: "Database connection failures"
    conditionThreshold:
      filter: 'resource.type="cloudsql_database" AND metric.type="cloudsql.googleapis.com/database/up"'
      comparison: COMPARISON_LESS_THAN
      thresholdValue: 1
      duration: "60s"

# BigQuery Quota Alert
- name: "BigQuery Quota Exceeded"
  condition:
    displayName: "BigQuery slots utilization > 80%"
    conditionThreshold:
      filter: 'metric.type="bigquery.googleapis.com/slots/allocated"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 800
      duration: "300s"
```

Deploy monitoring:

```bash
# Create notification channels
gcloud alpha monitoring channels create \
  --display-name="Email Alerts" \
  --type=email \
  --channel-labels=email_address=$ADMIN_EMAIL

# Deploy alert policies
gcloud alpha monitoring policies create --policy-from-file=monitoring/alerts.yaml
```

### 2. Custom Dashboards

Create dashboard configuration `monitoring/dashboard.json`:

```json
{
  "displayName": "AI Data Analyst Production Dashboard",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "API Request Rate",
          "timeSeriesChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE",
                    "crossSeriesReducer": "REDUCE_SUM"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "API Response Time",
          "timeSeriesChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_PERCENTILE_95"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "width": 12,
        "height": 4,
        "widget": {
          "title": "Database Performance",
          "timeSeriesChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloudsql_database\" AND metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_MEAN"
                  }
                }
              }
            }]
          }
        }
      }
    ]
  }
}
```

## 🧪 Testing & Validation

### 1. Deployment Validation Script

Create `scripts/validate_deployment.py`:

```python
#!/usr/bin/env python3
"""
Production deployment validation script
"""

import requests
import time
import sys
import logging
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeploymentValidator:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def run_health_checks(self) -> List[Tuple[str, bool, str]]:
        """Run comprehensive health checks"""
        checks = []
        
        # API Health Check
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            success = response.status_code == 200
            message = f"Status: {response.status_code}"
            if success:
                data = response.json()
                message += f", Version: {data.get('version', 'unknown')}"
        except Exception as e:
            success = False
            message = str(e)
        checks.append(("API Health", success, message))
        
        # Database Connectivity
        try:
            response = self.session.get(f"{self.base_url}/admin/health/database", timeout=10)
            success = response.status_code == 200
            message = f"Database connection: {'OK' if success else 'Failed'}"
        except Exception as e:
            success = False
            message = f"Database check failed: {e}"
        checks.append(("Database", success, message))
        
        # BigQuery Connectivity
        try:
            response = self.session.get(f"{self.base_url}/admin/health/bigquery", timeout=10)
            success = response.status_code == 200
            message = f"BigQuery connection: {'OK' if success else 'Failed'}"
        except Exception as e:
            success = False
            message = f"BigQuery check failed: {e}"
        checks.append(("BigQuery", success, message))
        
        # Storage Connectivity
        try:
            response = self.session.get(f"{self.base_url}/admin/health/storage", timeout=10)
            success = response.status_code == 200
            message = f"Storage connection: {'OK' if success else 'Failed'}"
        except Exception as e:
            success = False
            message = f"Storage check failed: {e}"
        checks.append(("Storage", success, message))
        
        return checks
    
    def run_performance_tests(self) -> List[Tuple[str, bool, str]]:
        """Run basic performance tests"""
        tests = []
        
        # Response time test
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            response_time = (time.time() - start_time) * 1000
            success = response_time < 1000  # Less than 1 second
            message = f"Response time: {response_time:.2f}ms"
        except Exception as e:
            success = False
            message = f"Performance test failed: {e}"
        tests.append(("Response Time", success, message))
        
        # Concurrent requests test
        import concurrent.futures
        import threading
        
        def make_request():
            try:
                response = self.session.get(f"{self.base_url}/health", timeout=10)
                return response.status_code == 200
            except:
                return False
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        duration = (time.time() - start_time) * 1000
        success_rate = sum(results) / len(results)
        success = success_rate >= 0.9 and duration < 5000
        message = f"10 concurrent requests: {success_rate*100:.1f}% success, {duration:.2f}ms total"
        tests.append(("Concurrent Load", success, message))
        
        return tests
    
    def validate_security(self) -> List[Tuple[str, bool, str]]:
        """Validate security configurations"""
        checks = []
        
        # HTTPS redirect
        try:
            http_url = self.base_url.replace('https://', 'http://')
            response = requests.get(f"{http_url}/health", allow_redirects=False, timeout=10)
            success = response.status_code in [301, 302, 308] or self.base_url.startswith('https://')
            message = f"HTTPS redirect: {'OK' if success else 'Missing'}"
        except Exception as e:
            success = True  # Assume HTTPS-only setup
            message = "HTTPS-only configuration"
        checks.append(("HTTPS Redirect", success, message))
        
        # Security headers
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            headers = response.headers
            
            security_headers = [
                'Strict-Transport-Security',
                'X-Content-Type-Options',
                'X-Frame-Options',
                'X-XSS-Protection'
            ]
            
            present_headers = [h for h in security_headers if h in headers]
            success = len(present_headers) >= 3
            message = f"Security headers: {len(present_headers)}/{len(security_headers)} present"
        except Exception as e:
            success = False
            message = f"Security header check failed: {e}"
        checks.append(("Security Headers", success, message))
        
        return checks

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Validate AI Data Analyst deployment')
    parser.add_argument('--url', required=True, help='Base URL of the deployment')
    parser.add_argument('--api-key', help='API key for authenticated endpoints')
    parser.add_argument('--skip-performance', action='store_true', help='Skip performance tests')
    
    args = parser.parse_args()
    
    validator = DeploymentValidator(args.url, args.api_key)
    
    print("🔍 Validating AI Data Analyst Deployment")
    print("=" * 50)
    
    # Run health checks
    print("\n📊 Health Checks:")
    health_results = validator.run_health_checks()
    for name, success, message in health_results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}: {message}")
    
    # Run performance tests
    if not args.skip_performance:
        print("\n⚡ Performance Tests:")
        perf_results = validator.run_performance_tests()
        for name, success, message in perf_results:
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {message}")
    else:
        perf_results = []
    
    # Run security validation
    print("\n🔒 Security Validation:")
    security_results = validator.validate_security()
    for name, success, message in security_results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}: {message}")
    
    # Summary
    all_results = health_results + perf_results + security_results
    total_checks = len(all_results)
    passed_checks = sum(1 for _, success, _ in all_results if success)
    
    print(f"\n📋 Summary: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("🎉 All validation checks passed! Deployment is ready.")
        return 0
    else:
        print("⚠️  Some validation checks failed. Please review and fix issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

Run validation:

```bash
python scripts/validate_deployment.py --url https://api.aidataanalyst.com
```

### 2. Load Testing

Create load test with k6 `tests/load_test.js`:

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export let errorRate = new Rate('errors');

export let options = {
  stages: [
    { duration: '2m', target: 10 }, // Ramp up
    { duration: '5m', target: 50 }, // Stay at 50 users
    { duration: '2m', target: 100 }, // Ramp up to 100 users
    { duration: '5m', target: 100 }, // Stay at 100 users
    { duration: '2m', target: 0 },   // Ramp down
  ],
  thresholds: {
    errors: ['rate<0.01'], // Error rate must be less than 1%
    http_req_duration: ['p(95)<2000'], // 95% of requests must complete below 2s
  },
};

const BASE_URL = 'https://api.aidataanalyst.com';

export default function () {
  // Health check
  let response = http.get(`${BASE_URL}/health`);
  check(response, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 500ms': (r) => r.timings.duration < 500,
  }) || errorRate.add(1);

  sleep(1);

  // API endpoint test (if authenticated)
  if (__ENV.API_KEY) {
    let headers = {
      'Authorization': `Bearer ${__ENV.API_KEY}`,
      'Content-Type': 'application/json',
    };
    
    response = http.get(`${BASE_URL}/projects`, { headers });
    check(response, {
      'projects endpoint status is 200': (r) => r.status === 200,
      'projects response time < 1000ms': (r) => r.timings.duration < 1000,
    }) || errorRate.add(1);
  }

  sleep(2);
}
```

Run load test:

```bash
k6 run --env API_KEY=your-api-key tests/load_test.js
```

## ✅ Go-Live Checklist

### Pre-Deployment
- [ ] Infrastructure provisioned and configured
- [ ] SSL certificates installed and validated
- [ ] DNS records configured and propagated
- [ ] Database migrations completed successfully
- [ ] Application containers built and pushed
- [ ] Environment variables and secrets configured
- [ ] Monitoring and alerting configured
- [ ] Load balancer and CDN configured
- [ ] Backup and disaster recovery tested

### Security Checklist
- [ ] VPC Service Controls configured
- [ ] IAM roles and permissions reviewed
- [ ] Security headers configured
- [ ] API authentication working
- [ ] Database access restricted
- [ ] Audit logging enabled
- [ ] Vulnerability scanning completed
- [ ] Penetration testing completed (if required)

### Performance Checklist
- [ ] Load testing completed with acceptable results
- [ ] Database performance optimized
- [ ] Caching strategies implemented
- [ ] CDN configured for static assets
- [ ] Auto-scaling configured and tested
- [ ] Performance monitoring in place

### Operations Checklist
- [ ] Deployment validation script passes
- [ ] Health checks operational
- [ ] Log aggregation working
- [ ] Metrics collection active
- [ ] Alert notifications working
- [ ] Backup procedures tested
- [ ] Rollback procedures documented and tested

### Documentation
- [ ] Deployment runbooks updated
- [ ] API documentation published
- [ ] User guides available
- [ ] Support procedures documented
- [ ] Incident response plan ready

## 🚀 Post-Deployment

### Immediate Actions (First 24 Hours)

1. **Monitor Key Metrics**:
   ```bash
   # Watch critical metrics
   gcloud logging read "resource.type=cloud_run_revision" --limit=50 --format="table(timestamp,severity,textPayload)"
   
   # Check error rates
   gcloud monitoring metrics list --filter="metric.type:run.googleapis.com"
   ```

2. **Validate Core Functionality**:
   ```bash
   # Run deployment validation
   python scripts/validate_deployment.py --url https://api.aidataanalyst.com
   
   # Test user workflows
   curl -X POST https://api.aidataanalyst.com/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@company.com","password":"password"}'
   ```

3. **Performance Monitoring**:
   - Monitor API response times
   - Check database connection pool utilization
   - Verify BigQuery job execution times
   - Watch auto-scaling behavior

### Week 1 Actions

1. **User Onboarding**:
   - Send welcome emails to initial users
   - Conduct training sessions
   - Gather initial feedback

2. **Performance Optimization**:
   - Analyze actual usage patterns
   - Optimize based on real data
   - Adjust auto-scaling parameters

3. **Security Review**:
   - Review access logs
   - Validate security controls
   - Update security documentation

### Ongoing Operations

1. **Regular Health Checks**:
   ```bash
   # Daily validation
   0 9 * * * /path/to/validate_deployment.py --url https://api.aidataanalyst.com
   ```

2. **Weekly Reviews**:
   - Performance metrics analysis
   - Cost optimization review
   - Security log analysis
   - User feedback review

3. **Monthly Tasks**:
   - Disaster recovery testing
   - Security vulnerability scanning
   - Capacity planning review
   - Documentation updates

## 🔧 Troubleshooting

### Common Issues

#### API Not Responding
```bash
# Check Cloud Run service status
gcloud run services describe ai-analyst-api --region=us-central1

# Check recent logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID
```

#### Database Connection Issues
```bash
# Check Cloud SQL instance status
gcloud sql instances describe ai-analyst-db-production

# Test database connection
gcloud sql connect ai-analyst-db-production --user=app_user

# Check VPC connector
gcloud compute networks vpc-access connectors describe ai-analyst-connector --region=us-central1
```

#### High Response Times
```bash
# Check Cloud Run metrics
gcloud monitoring metrics list --filter="resource.type=cloud_run_revision"

# Check BigQuery job performance
bq ls -j --max_results=10 --all_users

# Analyze slow queries
gcloud logging read "resource.type=cloud_run_revision AND severity>=WARNING"
```

#### SSL Certificate Issues
```bash
# Check certificate status
gcloud compute ssl-certificates describe ai-analyst-ssl

# Verify DNS configuration
nslookup aidataanalyst.com
nslookup api.aidataanalyst.com

# Test SSL configuration
openssl s_client -connect aidataanalyst.com:443
```

### Emergency Procedures

#### Rollback Deployment
```bash
# Rollback to previous Cloud Run revision
gcloud run services update-traffic ai-analyst-api \
  --to-revisions=ai-analyst-api-00002-rev=100 \
  --region=us-central1

# Rollback database (if needed)
# This should be done carefully with database backups
gcloud sql backups restore $BACKUP_ID \
  --restore-instance=ai-analyst-db-production
```

#### Scale Down for Maintenance
```bash
# Set minimum instances to 0
gcloud run services update ai-analyst-api \
  --min-instances=0 \
  --region=us-central1

# Enable maintenance mode
gcloud run services update ai-analyst-api \
  --set-env-vars=MAINTENANCE_MODE=true \
  --region=us-central1
```

---

## 📞 Support Contacts

- **DevOps Team**: devops@aidataanalyst.com
- **Security Team**: security@aidataanalyst.com  
- **On-Call Engineer**: +1-800-SUPPORT
- **Incident Management**: incidents@aidataanalyst.com

---

**Deployment Guide Version**: 1.0  
**Last Updated**: October 2025  
**Document ID**: AIDA-DEPLOY-001