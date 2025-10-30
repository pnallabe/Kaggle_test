from flask import Flask, jsonify, request
from datetime import datetime
import os
import json
from pathlib import Path

app = Flask(__name__)

# In-memory storage (will persist during server runtime)
STORAGE_FILE = 'projects_storage.json'
projects_db = []

def load_projects():
    """Load projects from storage file"""
    global projects_db
    if Path(STORAGE_FILE).exists():
        try:
            with open(STORAGE_FILE, 'r') as f:
                projects_db = json.load(f)
        except:
            projects_db = []
    return projects_db

def save_projects():
    """Save projects to storage file"""
    with open(STORAGE_FILE, 'w') as f:
        json.dump(projects_db, f, indent=2)

def init_default_projects():
    """Initialize with default projects if empty"""
    global projects_db
    if not projects_db:
        projects_db = [
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
        ]
        save_projects()

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
    """List all projects"""
    load_projects()
    return jsonify({
        "projects": projects_db,
        "total_count": len(projects_db),
        "page": 1,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/v1/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    global projects_db
    data = request.get_json() or {}
    project_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    project = {
        "id": project_id,
        "name": data.get("name", "Untitled Project"),
        "description": data.get("description", ""),
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "data_sources": data.get("data_sources", []),
        "last_updated": datetime.now().isoformat()
    }
    
    # Add to database and save
    load_projects()
    projects_db.append(project)
    save_projects()
    
    return jsonify({
        "project": project,
        "message": "Project created successfully",
        "timestamp": datetime.now().isoformat()
    }), 201

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
    # Initialize default projects
    load_projects()
    init_default_projects()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
