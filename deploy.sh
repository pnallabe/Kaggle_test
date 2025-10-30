#!/bin/bash

################################################################################
# AI Data Analyst - Full Stack Deployment Script
# 
# This script deploys both frontend and backend to various platforms:
# - Local (development)
# - Docker (containerized)
# - Cloud Run (Google Cloud)
# - Heroku (alternative)
# - AWS (alternative)
#
# Usage:
#   ./deploy.sh local          # Local development setup
#   ./deploy.sh docker         # Docker containerized deployment
#   ./deploy.sh cloud-run      # Google Cloud Run deployment
#   ./deploy.sh heroku         # Heroku deployment
#   ./deploy.sh aws            # AWS deployment
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_TARGET="${1:-local}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="ai-data-analyst"

# Print colored output
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Validate deployment target
validate_target() {
    case "$DEPLOYMENT_TARGET" in
        local|docker|cloud-run|heroku|aws)
            return 0
            ;;
        *)
            print_error "Invalid deployment target: $DEPLOYMENT_TARGET"
            echo "Valid targets: local, docker, cloud-run, heroku, aws"
            exit 1
            ;;
    esac
}

################################################################################
# LOCAL DEPLOYMENT (Development)
################################################################################

deploy_local() {
    print_header "Local Development Deployment"
    
    print_info "Setting up local development environment..."
    
    # Backend setup
    print_info "Configuring backend..."
    cd "$SCRIPT_DIR"
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python version: $PYTHON_VERSION"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv .venv
    fi
    
    # Activate virtual environment and install dependencies
    print_info "Installing backend dependencies..."
    source .venv/bin/activate
    pip install -q -r requirements.txt
    print_success "Backend dependencies installed"
    
    # Frontend setup
    print_info "Configuring frontend..."
    cd "$SCRIPT_DIR/frontend"
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install Node.js"
        exit 1
    fi
    
    NODE_VERSION=$(node --version)
    print_success "Node version: $NODE_VERSION"
    
    if [ ! -d "node_modules" ]; then
        print_info "Installing frontend dependencies..."
        npm install -q
    fi
    
    print_success "Frontend dependencies installed"
    
    # Create .env files if they don't exist
    if [ ! -f ".env.local" ]; then
        print_info "Creating .env.local for frontend..."
        cat > .env.local << 'EOF'
VITE_API_URL=http://localhost:8080
VITE_APP_NAME=AI Data Analyst
VITE_ENVIRONMENT=development
EOF
        print_success ".env.local created"
    fi
    
    # Create backend .env if it doesn't exist
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        print_info "Creating .env for backend..."
        cat > "$SCRIPT_DIR/.env" << 'EOF'
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production
PORT=8080
MAX_STORAGE_PER_USER_MB=100
JWT_EXPIRATION_HOURS=24
EOF
        print_success ".env created for backend"
    fi
    
    print_header "Local Deployment Complete"
    echo ""
    echo "To start the application:"
    echo ""
    echo "Terminal 1 - Backend:"
    echo "  cd $SCRIPT_DIR"
    echo "  source .venv/bin/activate"
    echo "  python main.py"
    echo ""
    echo "Terminal 2 - Frontend:"
    echo "  cd $SCRIPT_DIR/frontend"
    echo "  npm run dev"
    echo ""
    echo "Then open: http://localhost:3001"
    echo ""
}

################################################################################
# DOCKER DEPLOYMENT
################################################################################

deploy_docker() {
    print_header "Docker Deployment"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    print_success "Docker found: $(docker --version)"
    
    # Create Dockerfile for backend if it doesn't exist
    if [ ! -f "$SCRIPT_DIR/Dockerfile.backend" ]; then
        print_info "Creating Dockerfile for backend..."
        cat > "$SCRIPT_DIR/Dockerfile.backend" << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "main.py"]
EOF
        print_success "Dockerfile.backend created"
    fi
    
    # Create Dockerfile for frontend if it doesn't exist
    if [ ! -f "$SCRIPT_DIR/Dockerfile.frontend" ]; then
        print_info "Creating Dockerfile for frontend..."
        cat > "$SCRIPT_DIR/Dockerfile.frontend" << 'EOF'
# Build stage
FROM node:18-alpine as builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend .
RUN npm run build

# Runtime stage
FROM node:18-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
EOF
        print_success "Dockerfile.frontend created"
    fi
    
    # Build backend image
    print_info "Building backend Docker image..."
    docker build -t "$PROJECT_NAME-backend:$TIMESTAMP" -f Dockerfile.backend "$SCRIPT_DIR"
    docker tag "$PROJECT_NAME-backend:$TIMESTAMP" "$PROJECT_NAME-backend:latest"
    print_success "Backend image built"
    
    # Build frontend image
    print_info "Building frontend Docker image..."
    docker build -t "$PROJECT_NAME-frontend:$TIMESTAMP" -f Dockerfile.frontend "$SCRIPT_DIR"
    docker tag "$PROJECT_NAME-frontend:$TIMESTAMP" "$PROJECT_NAME-frontend:latest"
    print_success "Frontend image built"
    
    # Create docker-compose if it doesn't exist
    if [ ! -f "docker-compose.yml" ] || grep -q "version: '2'" docker-compose.yml; then
        print_info "Creating docker-compose.yml..."
        cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=your-secret-key-change-in-production
      - PORT=8080
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://backend:8080
    depends_on:
      - backend
    restart: unless-stopped
EOF
        print_success "docker-compose.yml created"
    fi
    
    print_header "Docker Deployment Complete"
    echo ""
    echo "To run with Docker Compose:"
    echo "  docker-compose up -d"
    echo ""
    echo "To view logs:"
    echo "  docker-compose logs -f"
    echo ""
    echo "To stop:"
    echo "  docker-compose down"
    echo ""
    echo "Frontend: http://localhost:3000"
    echo "Backend: http://localhost:8080"
    echo ""
}

################################################################################
# GOOGLE CLOUD RUN DEPLOYMENT
################################################################################

deploy_cloud_run() {
    print_header "Google Cloud Run Deployment"
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed"
        echo "Install from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    print_success "gcloud found: $(gcloud --version | head -1)"
    
    # Configuration
    read -p "Enter GCP Project ID: " PROJECT_ID
    read -p "Enter GCP Region (default: us-central1): " REGION
    REGION=${REGION:-us-central1}
    
    print_info "Project ID: $PROJECT_ID"
    print_info "Region: $REGION"
    
    # Set project
    gcloud config set project "$PROJECT_ID"
    
    # Enable APIs
    print_info "Enabling required Google Cloud APIs..."
    gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
    print_success "APIs enabled"
    
    # Create Artifact Registry repository
    print_info "Setting up Artifact Registry..."
    REPO_NAME="ai-analyst-repo"
    
    if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" &> /dev/null; then
        gcloud artifacts repositories create "$REPO_NAME" \
            --location="$REGION" \
            --repository-format=docker
        print_success "Artifact Registry repository created"
    else
        print_success "Artifact Registry repository already exists"
    fi
    
    # Build and deploy backend
    print_info "Building and deploying backend..."
    BACKEND_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/backend"
    
    gcloud builds submit --tag "$BACKEND_IMAGE:$TIMESTAMP" \
        --file Dockerfile.backend \
        "$SCRIPT_DIR"
    
    gcloud run deploy "$PROJECT_NAME-backend" \
        --image "$BACKEND_IMAGE:$TIMESTAMP" \
        --platform managed \
        --region "$REGION" \
        --memory 512Mi \
        --allow-unauthenticated \
        --set-env-vars="SECRET_KEY=your-secret-key-change-in-production,PORT=8080"
    
    BACKEND_URL=$(gcloud run services describe "$PROJECT_NAME-backend" --platform managed --region "$REGION" --format='value(status.url)')
    print_success "Backend deployed: $BACKEND_URL"
    
    # Build and deploy frontend
    print_info "Building and deploying frontend..."
    FRONTEND_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/frontend"
    
    # Update frontend .env with backend URL
    cat > frontend/.env.production << EOF
VITE_API_URL=$BACKEND_URL
VITE_APP_NAME=AI Data Analyst
VITE_ENVIRONMENT=production
EOF
    
    gcloud builds submit --tag "$FRONTEND_IMAGE:$TIMESTAMP" \
        --file Dockerfile.frontend \
        "$SCRIPT_DIR"
    
    gcloud run deploy "$PROJECT_NAME-frontend" \
        --image "$FRONTEND_IMAGE:$TIMESTAMP" \
        --platform managed \
        --region "$REGION" \
        --memory 256Mi \
        --allow-unauthenticated
    
    FRONTEND_URL=$(gcloud run services describe "$PROJECT_NAME-frontend" --platform managed --region "$REGION" --format='value(status.url)')
    print_success "Frontend deployed: $FRONTEND_URL"
    
    print_header "Cloud Run Deployment Complete"
    echo ""
    echo "Service URLs:"
    echo "  Frontend: $FRONTEND_URL"
    echo "  Backend: $BACKEND_URL"
    echo ""
}

################################################################################
# HEROKU DEPLOYMENT
################################################################################

deploy_heroku() {
    print_header "Heroku Deployment"
    
    if ! command -v heroku &> /dev/null; then
        print_error "Heroku CLI is not installed"
        echo "Install from: https://devcenter.heroku.com/articles/heroku-cli"
        exit 1
    fi
    
    read -p "Enter Heroku app name: " HEROKU_APP
    
    print_info "App name: $HEROKU_APP"
    
    # Create Procfile
    print_info "Creating Procfile..."
    cat > Procfile << 'EOF'
web: gunicorn -w 4 -b 0.0.0.0:$PORT main:app
release: python -m flask db upgrade
EOF
    print_success "Procfile created"
    
    # Create Heroku app
    if heroku apps:info "$HEROKU_APP" &> /dev/null; then
        print_success "Heroku app already exists"
    else
        print_info "Creating Heroku app..."
        heroku create "$HEROKU_APP"
        print_success "Heroku app created"
    fi
    
    # Set environment variables
    print_info "Setting environment variables..."
    heroku config:set --app="$HEROKU_APP" \
        SECRET_KEY="$(openssl rand -base64 32)" \
        FLASK_ENV=production
    print_success "Environment variables set"
    
    # Deploy
    print_info "Deploying to Heroku..."
    git push heroku main
    print_success "Deployed to Heroku"
    
    print_header "Heroku Deployment Complete"
    echo ""
    echo "App URL: https://$HEROKU_APP.herokuapp.com"
    echo ""
    echo "View logs:"
    echo "  heroku logs --app=$HEROKU_APP -t"
    echo ""
}

################################################################################
# AWS DEPLOYMENT
################################################################################

deploy_aws() {
    print_header "AWS Deployment"
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        echo "Install from: https://aws.amazon.com/cli/"
        exit 1
    fi
    
    print_success "AWS CLI found: $(aws --version)"
    
    read -p "Enter AWS Region (default: us-east-1): " AWS_REGION
    AWS_REGION=${AWS_REGION:-us-east-1}
    
    read -p "Enter ECR Repository name (default: ai-data-analyst): " ECR_REPO
    ECR_REPO=${ECR_REPO:-ai-data-analyst}
    
    # Get AWS Account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    print_success "AWS Account ID: $ACCOUNT_ID"
    
    # Create ECR repositories
    print_info "Creating ECR repositories..."
    for service in backend frontend; do
        if aws ecr describe-repositories --repository-names "$ECR_REPO-$service" --region "$AWS_REGION" &> /dev/null; then
            print_success "ECR repository $ECR_REPO-$service already exists"
        else
            aws ecr create-repository --repository-name "$ECR_REPO-$service" --region "$AWS_REGION"
            print_success "ECR repository $ECR_REPO-$service created"
        fi
    done
    
    # Login to ECR
    print_info "Logging into ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    print_success "Logged into ECR"
    
    # Build and push backend
    print_info "Building and pushing backend image..."
    BACKEND_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO-backend:$TIMESTAMP"
    docker build -t "$BACKEND_URI" -f Dockerfile.backend .
    docker push "$BACKEND_URI"
    print_success "Backend image pushed"
    
    # Build and push frontend
    print_info "Building and pushing frontend image..."
    FRONTEND_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO-frontend:$TIMESTAMP"
    docker build -t "$FRONTEND_URI" -f Dockerfile.frontend .
    docker push "$FRONTEND_URI"
    print_success "Frontend image pushed"
    
    print_header "AWS Deployment Complete"
    echo ""
    echo "Images pushed to ECR:"
    echo "  Backend: $BACKEND_URI"
    echo "  Frontend: $FRONTEND_URI"
    echo ""
    echo "Next steps:"
    echo "  1. Create ECS Cluster"
    echo "  2. Create Task Definitions"
    echo "  3. Create Services"
    echo "  4. Configure Load Balancer"
    echo ""
}

################################################################################
# MAIN SCRIPT
################################################################################

main() {
    print_header "$PROJECT_NAME - Full Stack Deployment"
    echo "Target: $DEPLOYMENT_TARGET"
    echo "Timestamp: $TIMESTAMP"
    echo ""
    
    validate_target
    
    case "$DEPLOYMENT_TARGET" in
        local)
            deploy_local
            ;;
        docker)
            deploy_docker
            ;;
        cloud-run)
            deploy_cloud_run
            ;;
        heroku)
            deploy_heroku
            ;;
        aws)
            deploy_aws
            ;;
    esac
    
    print_success "Deployment process completed!"
    echo ""
}

# Run main function
main "$@"
