# Phase 1: Foundations - Implementation Guide

## Overview

This guide covers setting up the baseline infrastructure and API framework for the AI Data Analyst platform on GCP.

## Prerequisites

- GCP Project with billing enabled
- `gcloud` CLI installed and configured
- `terraform` >= 1.0
- Docker installed (for local testing)
- `git` for version control

## Architecture Components

### 1. GCP Resources (Terraform)

- **VPC Network**: Private VPC with Cloud SQL private service connection
- **Cloud SQL**: PostgreSQL 15 database for metadata
- **BigQuery**: Analytics and audit datasets
- **Cloud Storage**: Artifact and backend storage buckets
- **Pub/Sub**: Job queue for worker orchestration
- **Cloud Run**: Serverless API and worker services
- **Memorystore (Redis)**: Distributed caching layer
- **Secret Manager**: Secure credential storage
- **Cloud KMS**: Encryption key management
- **Cloud Logging**: Centralized logging
- **Cloud Monitoring**: Metrics and alerts

### 2. API Backend (FastAPI)

- FastAPI + Uvicorn for HTTP server
- SQLAlchemy ORM for database access
- Google Auth for JWT validation
- Role-based access control (RBAC)
- Audit logging

### 3. Authentication (Identity Platform)

- OAuth 2.0 / OpenID Connect
- JWT validation
- User onboarding

### 4. CI/CD (Cloud Build)

- Automated testing
- Docker image building
- Container registry storage
- Cloud Run deployment

---

## Setup Steps

### Step 1: Prepare GCP Project

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"

# Authenticate with gcloud
gcloud auth login
gcloud config set project $PROJECT_ID

# Create a service account for Terraform
gcloud iam service-accounts create terraform-admin \
    --display-name="Terraform Admin"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:terraform-admin@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/editor"

# Create and download key
gcloud iam service-accounts keys create ~/terraform-key.json \
    --iam-account=terraform-admin@${PROJECT_ID}.iam.gserviceaccount.com

# Set Terraform credentials
export GOOGLE_APPLICATION_CREDENTIALS=~/terraform-key.json
```

### Step 2: Create Terraform State Bucket

```bash
# Create GCS bucket for Terraform state
gsutil mb -p $PROJECT_ID -l $REGION \
    gs://${PROJECT_ID}-terraform-state

# Enable versioning
gsutil versioning set on gs://${PROJECT_ID}-terraform-state

# Enable uniform bucket-level access
gsutil uniformbucketlevelaccess set on gs://${PROJECT_ID}-terraform-state
```

### Step 3: Initialize Terraform

```bash
cd infra/

# Copy and customize variables
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your project settings
# - project_id: your GCP project ID
# - region: your preferred region
# - environment: dev, staging, or prod

# Initialize Terraform
terraform init \
    -backend-config="bucket=${PROJECT_ID}-terraform-state" \
    -backend-config="prefix=ai-data-analyst"

# Validate configuration
terraform validate

# Plan infrastructure
terraform plan -out=tfplan.out
```

### Step 4: Deploy Infrastructure

```bash
# Apply Terraform plan
terraform apply tfplan.out

# Capture outputs
terraform output -json > outputs.json

# Export key values for later use
export GCS_ARTIFACTS_BUCKET=$(terraform output -raw gcs_artifacts_bucket)
export GCS_BACKEND_BUCKET=$(terraform output -raw gcs_backend_bucket)
export CLOUD_SQL_CONNECTION=$(terraform output -raw cloud_sql_instance)
export BQ_ANALYTICS_DATASET=$(terraform output -raw bigquery_analytics_dataset)
export BQ_AUDIT_DATASET=$(terraform output -raw bigquery_audit_dataset)
export PUBSUB_JOB_TOPIC=$(terraform output -raw pubsub_job_topic)
export CLOUD_RUN_API_URL=$(terraform output -raw cloud_run_api_url)
export API_SA_EMAIL=$(terraform output -raw api_service_account_email)
export REDIS_HOST=$(terraform output -raw redis_host)
export REDIS_PORT=$(terraform output -raw redis_port)
export DB_CONNECTION_SECRET=$(terraform output -raw db_connection_secret)
```

### Step 5: Initialize Cloud SQL Database

```bash
# Get Cloud SQL instance connection name
INSTANCE_CONNECTION_NAME=$(terraform output -raw cloud_sql_instance)

# Create proxy to Cloud SQL
cloud_sql_proxy -instances=${INSTANCE_CONNECTION_NAME}=tcp:5432 &

# Run schema initialization
export DATABASE_URL="postgresql://api_service:PASSWORD@localhost:5432/ai_analyst"
psql $DATABASE_URL < infra/schema.sql

# Stop proxy
kill %1
```

### Step 6: Build and Push Docker Image

```bash
# Set up Artifact Registry
gcloud artifacts repositories create docker-repo \
    --repository-format=docker \
    --location=$REGION

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build Docker image
cd api/
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/api:latest .

# Push to Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/api:latest
```

### Step 7: Deploy API to Cloud Run

```bash
# Get environment variables from Terraform outputs
export DB_HOST=$(terraform output -raw cloud_sql_private_ip)
export REDIS_HOST=$(terraform output -raw redis_host)
export REDIS_PORT=$(terraform output -raw redis_port)

# Deploy service
gcloud run deploy ai-data-analyst \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/api:latest \
    --region=$REGION \
    --platform=managed \
    --memory=2Gi \
    --cpu=2 \
    --timeout=3600s \
    --service-account=${API_SA_EMAIL} \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},DATABASE_URL=postgresql://api_service@${DB_HOST}:5432/ai_analyst,REDIS_HOST=${REDIS_HOST},REDIS_PORT=${REDIS_PORT},BQ_ANALYTICS_DATASET=${BQ_ANALYTICS_DATASET},GCS_ARTIFACTS_BUCKET=${GCS_ARTIFACTS_BUCKET}" \
    --allow-unauthenticated
```

### Step 8: Set Up Identity Platform

```bash
# Enable Identity Platform
gcloud services enable identitytoolkit.googleapis.com

# Create OAuth client for web application
gcloud auth application-default login

# Get OAuth configuration details
gcloud identity-aware-proxy oauth-brands list

# Configure OAuth consent screen in Cloud Console
# Settings > Authentication > OAuth configuration
```

### Step 9: Set Up CI/CD with Cloud Build

```bash
# Create Artifact Registry repository
gcloud artifacts repositories create docker-repo \
    --repository-format=docker \
    --location=$REGION

# Connect GitHub/Cloud Source repository
# Cloud Build > Repositories > Connect

# Grant Cloud Build service account permissions
export CLOUD_BUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/iam.serviceAccountUser"
```

### Step 10: Configure Monitoring and Alerts

```bash
# Create notification channel (email)
gcloud alpha monitoring channels create \
    --display-name="AI Analyst Alerts" \
    --type="email" \
    --channel-labels=email_address=your-email@example.com

# Create alert policy for high error rates
# See monitoring/alert-policies.tf in Terraform
```

---

## Post-Deployment Verification

### 1. Test API Endpoints

```bash
# Get Cloud Run service URL
export API_URL=$(gcloud run services describe ai-data-analyst \
    --region=$REGION \
    --format='value(status.url)')

# Test health endpoint
curl ${API_URL}/health

# Test API documentation
curl ${API_URL}/docs
```

### 2. Verify Database Connection

```bash
# Check Cloud SQL connection
gcloud sql connect ai-data-analyst-postgres \
    --user=api_service \
    --project=$PROJECT_ID

# Query test (from connected shell)
SELECT COUNT(*) FROM users;
```

### 3. Test Authentication Flow

```bash
# Create test user in Identity Platform
gcloud identity-aware-proxy auth-sessions create \
    --project=$PROJECT_ID \
    --access_level="accessPolicies/0/accessLevels/cromwell_example"

# Generate test JWT and validate with API
# (See tests/auth_test.py for implementation details)
```

### 4. Verify GCS and BigQuery Access

```bash
# Test artifact upload
gsutil cp test-file.csv gs://${GCS_ARTIFACTS_BUCKET}/test/

# Test BigQuery dataset access
bq ls --project_id=$PROJECT_ID ${BQ_ANALYTICS_DATASET}
```

---

## Environment Configuration

Create `.env.local` for local development:

```
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
DATABASE_URL=postgresql://api_service:password@localhost:5432/ai_analyst
REDIS_HOST=localhost
REDIS_PORT=6379
BQ_ANALYTICS_DATASET=analytics
BQ_AUDIT_DATASET=audit
GCS_ARTIFACTS_BUCKET=your-project-artifacts-xxx
JWT_AUDIENCE=your-oauth-client-id
DEBUG=true
```

---

## Local Development

### Run API Locally

```bash
cd api/

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload

# API available at http://localhost:8080
```

### Run Tests

```bash
cd api/

# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v
```

---

## Cleanup

To remove all GCP resources (use with caution):

```bash
cd infra/

# Plan destruction
terraform plan -destroy -out=tfplan.destroy

# Apply destruction
terraform apply tfplan.destroy

# Clean up state bucket
gsutil -m rm -r gs://${PROJECT_ID}-terraform-state
```

---

## Troubleshooting

### Cloud SQL Connection Issues

```bash
# Check connectivity
gcloud sql connect ai-data-analyst-postgres \
    --user=postgres \
    --project=$PROJECT_ID

# Check network configuration
gcloud compute networks describe ai-data-analyst-vpc

# Review Cloud SQL logs
gcloud logging read "resource.type=cloudsql_database" \
    --project=$PROJECT_ID \
    --limit=50 \
    --format=json
```

### Cloud Run Deployment Issues

```bash
# Check service status
gcloud run services describe ai-data-analyst \
    --region=$REGION \
    --format=json

# View logs
gcloud logging read "resource.type=cloud_run_revision" \
    --project=$PROJECT_ID \
    --limit=50

# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:${API_SA_EMAIL}"
```

---

## Next Steps

1. **Phase 2**: Implement data ingestion pipelines (Dataflow + BigQuery)
2. **Phase 3**: Integrate Vertex AI for LLM and embeddings
3. **Phase 4**: Add visualization and reporting capabilities
4. **Phase 5**: Implement multi-tenancy and advanced security

---

## References

- [GCP Documentation](https://cloud.google.com/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Cloud Run Best Practices](https://cloud.google.com/run/docs/quickstarts/build-and-deploy)
