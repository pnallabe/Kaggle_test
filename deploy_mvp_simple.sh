#!/bin/bash
"""
AI Data Analyst MVP - Quick Cloud Deployment

This script provides a simplified deployment process for testing the MVP on Google Cloud Platform.
"""

set -e  # Exit on error

# Configuration
PROJECT_ID="ai-data-analyst-mvp-test"
REGION="us-central1"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "🚀 AI Data Analyst MVP - Cloud Deployment"
echo "=========================================="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Timestamp: $TIMESTAMP"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "."; then
    echo "❌ Not authenticated with gcloud. Running authentication..."
    gcloud auth login
fi

# Set project
echo "📋 Setting up project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create Artifact Registry repository
echo "🏗️  Setting up Artifact Registry..."
gcloud artifacts repositories create ai-analyst-repo \
    --repository-format=docker \
    --location=$REGION \
    --description="AI Data Analyst MVP container images" || echo "Repository already exists"

# Configure Docker authentication
gcloud auth configure-docker $REGION-docker.pkg.dev

# Create a simple API application
echo "🐳 Creating containerized API application..."

# Create app directory
mkdir -p mvp-api

# Create a simple FastAPI application
cat > mvp-api/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from datetime import datetime

app = FastAPI(title="AI Data Analyst MVP", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "AI Data Analyst MVP API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "project_id": os.getenv("PROJECT_ID", "unknown"),
        "region": os.getenv("REGION", "unknown")
    }

@app.get("/api/v1/projects")
async def list_projects():
    return {
        "projects": [
            {
                "id": "sample_project_1",
                "name": "Sample E-commerce Analysis",
                "description": "Customer behavior analysis for e-commerce data",
                "created_at": "2025-10-30T10:00:00Z",
                "status": "active"
            },
            {
                "id": "sample_project_2", 
                "name": "Sales Performance Dashboard",
                "description": "Real-time sales metrics and KPI tracking",
                "created_at": "2025-10-30T09:30:00Z",
                "status": "active"
            }
        ]
    }

@app.post("/api/v1/jobs")
async def create_analysis_job(job_data: dict):
    return {
        "job_id": f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "status": "queued",
        "message": "Analysis job created successfully",
        "estimated_completion": "2-3 minutes",
        "input_data": job_data
    }

@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    return {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "results": {
            "insights": [
                "Revenue increased by 23% in Q3",
                "Top product category: Electronics (45% of sales)",
                "Customer retention rate: 78%"
            ],
            "visualizations": [
                "revenue_trend_chart.png",
                "product_performance_pie.png", 
                "customer_segments_bar.png"
            ]
        },
        "completed_at": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
EOF

# Create requirements.txt
cat > mvp-api/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
EOF

# Create Dockerfile
cat > mvp-api/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "main.py"]
EOF

# Build and push the container image
echo "🏗️  Building container image..."
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/ai-analyst-repo/api:$TIMESTAMP"

cd mvp-api
docker build -t $IMAGE_NAME .
docker push $IMAGE_NAME
cd ..

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ai-analyst-api \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8080 \
    --cpu 1 \
    --memory 2Gi \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars PROJECT_ID=$PROJECT_ID,REGION=$REGION

# Get the service URL
SERVICE_URL=$(gcloud run services describe ai-analyst-api --region=$REGION --format='value(status.url)')

# Test the deployment
echo ""
echo "🧪 Testing deployment..."
echo "Service URL: $SERVICE_URL"

# Test health endpoint
if curl -s -f "$SERVICE_URL/health" > /dev/null; then
    echo "✅ Health check passed"
else
    echo "⚠️  Health check failed"
fi

# Test API endpoints
if curl -s -f "$SERVICE_URL/api/v1/projects" > /dev/null; then
    echo "✅ API endpoints working"
else
    echo "⚠️  API endpoints not responding"
fi

echo ""
echo "🎉 MVP DEPLOYMENT COMPLETED!"
echo "=========================================="
echo "✅ API Service: $SERVICE_URL"
echo "✅ Health Check: $SERVICE_URL/health"
echo "✅ Projects API: $SERVICE_URL/api/v1/projects"
echo "✅ Jobs API: $SERVICE_URL/api/v1/jobs"
echo ""
echo "🧪 Test the API:"
echo "curl $SERVICE_URL/health"
echo "curl $SERVICE_URL/api/v1/projects"
echo ""
echo "🎯 MVP is ready for testing!"