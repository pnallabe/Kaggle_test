#!/bin/bash

# AI Data Analyst - Quick Start Setup Script
# This script automates the initial GCP and infrastructure setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AI Data Analyst - Phase 1 Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}✗ $1 is not installed${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ $1 is installed${NC}"
    fi
}

check_command gcloud
check_command terraform
check_command docker
check_command python3

echo ""

# Get project configuration
echo -e "${YELLOW}Enter GCP Configuration:${NC}"
read -p "GCP Project ID: " PROJECT_ID
read -p "GCP Region (default: us-central1): " REGION
REGION=${REGION:-us-central1}

echo ""
echo -e "${YELLOW}Authenticating with GCP...${NC}"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}Enabling required GCP APIs...${NC}"
gcloud services enable \
    compute.googleapis.com \
    cloudsql.googleapis.com \
    storage.googleapis.com \
    bigquery.googleapis.com \
    pubsub.googleapis.com \
    run.googleapis.com \
    cloudkms.googleapis.com \
    secretmanager.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    --project=$PROJECT_ID

echo -e "${GREEN}✓ APIs enabled${NC}"

# Create Terraform state bucket
echo ""
echo -e "${YELLOW}Creating Terraform state bucket...${NC}"
STATE_BUCKET="${PROJECT_ID}-terraform-state"

if gsutil ls gs://${STATE_BUCKET} &>/dev/null; then
    echo -e "${GREEN}✓ State bucket already exists${NC}"
else
    gsutil mb -p $PROJECT_ID -l $REGION gs://${STATE_BUCKET}
    gsutil versioning set on gs://${STATE_BUCKET}
    gsutil uniformbucketlevelaccess set on gs://${STATE_BUCKET}
    echo -e "${GREEN}✓ State bucket created${NC}"
fi

# Create Terraform service account
echo ""
echo -e "${YELLOW}Setting up Terraform service account...${NC}"
TF_SA="terraform-admin@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe $TF_SA --project=$PROJECT_ID &>/dev/null; then
    echo -e "${GREEN}✓ Service account already exists${NC}"
else
    gcloud iam service-accounts create terraform-admin \
        --display-name="Terraform Admin" \
        --project=$PROJECT_ID
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$TF_SA" \
        --role="roles/editor"
    
    gcloud iam service-accounts keys create ~/terraform-key.json \
        --iam-account=$TF_SA \
        --project=$PROJECT_ID
    
    echo -e "${GREEN}✓ Service account created${NC}"
fi

# Initialize Terraform
echo ""
echo -e "${YELLOW}Initializing Terraform...${NC}"
cd infra

# Create terraform.tfvars if it doesn't exist
if [ ! -f terraform.tfvars ]; then
    cat > terraform.tfvars << EOF
project_id = "$PROJECT_ID"
region     = "$REGION"
app_name   = "ai-data-analyst"
environment = "dev"
db_machine_type = "db-f1-micro"
EOF
    echo -e "${GREEN}✓ Created terraform.tfvars${NC}"
fi

# Initialize Terraform backend
export GOOGLE_APPLICATION_CREDENTIALS=~/terraform-key.json

terraform init \
    -backend-config="bucket=${STATE_BUCKET}" \
    -backend-config="prefix=ai-data-analyst" \
    -backend-config="region=${REGION}"

echo -e "${GREEN}✓ Terraform initialized${NC}"

# Validate Terraform
echo ""
echo -e "${YELLOW}Validating Terraform configuration...${NC}"
terraform validate
echo -e "${GREEN}✓ Configuration valid${NC}"

# Plan Terraform
echo ""
echo -e "${YELLOW}Planning infrastructure deployment...${NC}"
terraform plan -out=tfplan.out -var-file="terraform.tfvars"

# Ask for confirmation
echo ""
read -p "Review plan above. Deploy? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo -e "${RED}✗ Deployment cancelled${NC}"
    exit 1
fi

# Apply Terraform
echo ""
echo -e "${YELLOW}Deploying infrastructure...${NC}"
terraform apply tfplan.out

# Export outputs
echo ""
echo -e "${YELLOW}Exporting resource outputs...${NC}"
terraform output -json > outputs.json

export GCS_ARTIFACTS_BUCKET=$(terraform output -raw gcs_artifacts_bucket)
export CLOUD_SQL_CONNECTION=$(terraform output -raw cloud_sql_instance)
export BQ_ANALYTICS_DATASET=$(terraform output -raw bigquery_analytics_dataset)

echo -e "${GREEN}✓ Infrastructure deployed${NC}"

# Setup Docker
echo ""
echo -e "${YELLOW}Setting up Docker for Artifact Registry...${NC}"
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Create Artifact Registry repository
echo -e "${YELLOW}Creating Artifact Registry repository...${NC}"
if gcloud artifacts repositories describe docker-repo --location=$REGION &>/dev/null; then
    echo -e "${GREEN}✓ Repository already exists${NC}"
else
    gcloud artifacts repositories create docker-repo \
        --repository-format=docker \
        --location=$REGION
    echo -e "${GREEN}✓ Repository created${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Review outputs in: infra/outputs.json"
echo "2. Initialize Cloud SQL database: see PHASE_1_SETUP.md"
echo "3. Build API image: cd api && docker build -t api ."
echo "4. Deploy to Cloud Run: see PHASE_1_SETUP.md"
echo ""
echo "Documentation:"
echo "- Setup guide: PHASE_1_SETUP.md"
echo "- Checklist: PHASE_1_CHECKLIST.md"
echo "- API docs: README_IMPLEMENTATION.md"
echo ""
