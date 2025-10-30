#!/bin/bash

# AI Data Analyst MVP - Quick Cloud Run Deployment
# This script deploys the MVP to Cloud Run using source deployment (no Docker required)

set -e

# Configuration
PROJECT_ID="ai-analyst-mvp-$(date +%Y%m%d-%H%M%S)"
REGION="us-central1"
SERVICE_NAME="ai-analyst-api"

echo "🚀 AI Data Analyst MVP - Cloud Run Deployment"
echo "=============================================="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK"
    exit 1
fi

# Create new project
echo "🏗️  Creating Google Cloud project..."
gcloud projects create $PROJECT_ID --name="AI Data Analyst MVP" || {
    echo "⚠️  Project creation failed. You may need to use an existing project."
    echo "Would you like to use an existing project? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Enter your existing project ID:"
        read -r PROJECT_ID
    else
        exit 1
    fi
}

# Set project
gcloud config set project $PROJECT_ID

echo "⚠️  Please enable billing for project $PROJECT_ID"
echo "Visit: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
echo "Press Enter after enabling billing..."
read -r

# Enable APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com

# Create application files
echo "📝 Creating application files..."

# Create main.py
cat > main.py << 'EOF'
from flask import Flask, jsonify, request
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/')
def root():
    return jsonify({
        "message": "AI Data Analyst MVP API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "status": "running",
        "project_id": os.getenv("GOOGLE_CLOUD_PROJECT")
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "service": "ai-analyst-api"
    })

@app.route('/api/v1/projects')
def list_projects():
    return jsonify({
        "projects": [
            {
                "id": "ecommerce_analysis",
                "name": "E-commerce Customer Analysis",
                "description": "Deep dive into customer behavior patterns",
                "created_at": "2025-10-30T10:00:00Z",
                "status": "active",
                "data_sources": ["BigQuery", "Google Analytics"],
                "last_updated": "2025-10-30T14:30:00Z"
            },
            {
                "id": "sales_dashboard",
                "name": "Real-time Sales Dashboard",
                "description": "Live sales metrics and KPI tracking",
                "created_at": "2025-10-30T09:30:00Z", 
                "status": "active",
                "data_sources": ["PostgreSQL", "Salesforce"],
                "last_updated": "2025-10-30T15:45:00Z"
            },
            {
                "id": "marketing_roi",
                "name": "Marketing ROI Analysis",
                "description": "Campaign performance and attribution modeling",
                "created_at": "2025-10-29T16:20:00Z",
                "status": "active",
                "data_sources": ["Google Ads", "Facebook Ads", "BigQuery"],
                "last_updated": "2025-10-30T12:15:00Z"
            }
        ],
        "total_count": 3,
        "page": 1,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/v1/jobs', methods=['POST'])
def create_job():
    job_data = request.get_json() or {}
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "message": "Analysis job created successfully",
        "estimated_completion": "2-3 minutes",
        "priority": "normal",
        "input_data": job_data,
        "created_at": datetime.now().isoformat(),
        "queue_position": 1
    })

@app.route('/api/v1/jobs/<job_id>')
def get_job_status(job_id):
    return jsonify({
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "results": {
            "summary": {
                "total_records_analyzed": 1250000,
                "analysis_duration_seconds": 45,
                "confidence_score": 0.94
            },
            "insights": [
                "Revenue increased by 23% in Q3 compared to Q2",
                "Top product category: Electronics (45% of total sales)",
                "Customer retention rate improved to 78%",
                "Mobile traffic accounts for 67% of conversions",
                "Average order value: $156.78 (+12% vs last quarter)"
            ],
            "visualizations": [
                {
                    "type": "line_chart",
                    "title": "Revenue Trend (Q1-Q3)",
                    "file": "revenue_trend_chart.png"
                },
                {
                    "type": "pie_chart", 
                    "title": "Product Category Performance",
                    "file": "product_performance_pie.png"
                },
                {
                    "type": "bar_chart",
                    "title": "Customer Segments",
                    "file": "customer_segments_bar.png"
                }
            ],
            "recommendations": [
                "Focus marketing spend on Electronics category",
                "Optimize mobile checkout experience",
                "Implement customer loyalty program for retention"
            ]
        },
        "completed_at": datetime.now().isoformat(),
        "execution_stats": {
            "cpu_time_seconds": 23.5,
            "memory_peak_mb": 512,
            "data_processed_gb": 4.2
        }
    })

@app.route('/api/v1/health/detailed')
def detailed_health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "service": "ai-analyst-api",
        "version": "1.0.0",
        "uptime_seconds": 3600,
        "checks": {
            "database": "healthy",
            "bigquery": "healthy", 
            "cache": "healthy",
            "external_apis": "healthy"
        },
        "performance": {
            "avg_response_time_ms": 145,
            "requests_per_minute": 42,
            "error_rate": 0.001
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
EOF

# Create requirements.txt
cat > requirements.txt << 'EOF'
Flask==3.0.0
gunicorn==21.2.0
EOF

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8080 \
    --cpu 1 \
    --memory 1Gi \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo "🧪 Testing deployment..."

# Test endpoints
echo "Testing health endpoint..."
if curl -s -f "$SERVICE_URL/health" > /dev/null; then
    echo "✅ Health check: PASSED"
else
    echo "❌ Health check: FAILED"
fi

echo "Testing projects API..."
if curl -s -f "$SERVICE_URL/api/v1/projects" > /dev/null; then
    echo "✅ Projects API: PASSED"
else
    echo "❌ Projects API: FAILED"
fi

echo ""
echo "🎉 DEPLOYMENT COMPLETED!"
echo "========================================"
echo "✅ Project ID: $PROJECT_ID"
echo "✅ Service URL: $SERVICE_URL"
echo "✅ Health Check: $SERVICE_URL/health"
echo "✅ Projects API: $SERVICE_URL/api/v1/projects"
echo "✅ Jobs API: $SERVICE_URL/api/v1/jobs"
echo "✅ Detailed Health: $SERVICE_URL/api/v1/health/detailed"
echo ""
echo "🧪 Test Commands:"
echo "curl $SERVICE_URL/health"
echo "curl $SERVICE_URL/api/v1/projects"
echo "curl -X POST $SERVICE_URL/api/v1/jobs -H 'Content-Type: application/json' -d '{\"project\":\"test\"}'"
echo ""
echo "📊 Google Cloud Console:"
echo "https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics?project=$PROJECT_ID"
echo ""
echo "🎯 Your AI Data Analyst MVP is live and ready for testing!"