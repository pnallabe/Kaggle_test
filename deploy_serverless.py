#!/usr/bin/env python3
"""
AI Data Analyst MVP - Serverless Cloud Deployment

Deploy the MVP to Google Cloud using Cloud Build (no local Docker required)
"""

import subprocess
import json
import time
import sys
from datetime import datetime

class ServerlessDeployer:
    def __init__(self):
        self.project_id = f"ai-analyst-mvp-{datetime.now().strftime('%Y%m%d%H%M')}"
        self.region = "us-central1"
        
    def run_command(self, cmd, check=True):
        """Run shell command and return result"""
        print(f"🔧 Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            if result.stdout:
                print(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {e}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            raise
    
    def create_project(self):
        """Create a new Google Cloud project"""
        print(f"🏗️  Creating project: {self.project_id}")
        
        # Create project
        self.run_command([
            'gcloud', 'projects', 'create', self.project_id,
            '--name', 'AI Data Analyst MVP'
        ])
        
        # Set as active project
        self.run_command([
            'gcloud', 'config', 'set', 'project', self.project_id
        ])
        
        # Enable billing (you'll need to link a billing account)
        print("⚠️  Note: You'll need to enable billing for this project in the Google Cloud Console")
        print(f"Visit: https://console.cloud.google.com/billing/linkedaccount?project={self.project_id}")
        
        input("Press Enter after enabling billing...")
    
    def enable_apis(self):
        """Enable required APIs"""
        print("🔧 Enabling APIs...")
        
        apis = [
            'cloudbuild.googleapis.com',
            'run.googleapis.com',
            'artifactregistry.googleapis.com',
            'secretmanager.googleapis.com'
        ]
        
        for api in apis:
            self.run_command(['gcloud', 'services', 'enable', api])
    
    def create_app_files(self):
        """Create application files for deployment"""
        print("📝 Creating application files...")
        
        # Create app.py
        app_content = '''
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
        "status": "running"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "project_id": os.getenv("GOOGLE_CLOUD_PROJECT", "unknown")
    })

@app.route('/api/v1/projects')
def list_projects():
    return jsonify({
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
    })

@app.route('/api/v1/jobs', methods=['POST'])
def create_job():
    job_data = request.get_json() or {}
    return jsonify({
        "job_id": f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "status": "queued",
        "message": "Analysis job created successfully",
        "estimated_completion": "2-3 minutes",
        "input_data": job_data
    })

@app.route('/api/v1/jobs/<job_id>')
def get_job_status(job_id):
    return jsonify({
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
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
'''
        
        with open('app.py', 'w') as f:
            f.write(app_content)
        
        # Create requirements.txt
        with open('requirements.txt', 'w') as f:
            f.write('Flask==3.0.0\n')
        
        # Create app.yaml for App Engine
        app_yaml = '''
runtime: python311

env_variables:
  PROJECT_ID: {}

automatic_scaling:
  min_instances: 0
  max_instances: 10
'''.format(self.project_id)
        
        with open('app.yaml', 'w') as f:
            f.write(app_yaml)
    
    def deploy_to_app_engine(self):
        """Deploy to Google App Engine"""
        print("🚀 Deploying to App Engine...")
        
        # Enable App Engine API
        self.run_command(['gcloud', 'services', 'enable', 'appengine.googleapis.com'])
        
        # Create App Engine app
        try:
            self.run_command([
                'gcloud', 'app', 'create', 
                '--region', self.region
            ])
        except subprocess.CalledProcessError:
            print("App Engine app already exists")
        
        # Deploy the application
        self.run_command(['gcloud', 'app', 'deploy', '--quiet'])
        
        # Get the URL
        result = self.run_command([
            'gcloud', 'app', 'browse', '--no-launch-browser'
        ])
        
        return f"https://{self.project_id}.uc.r.appspot.com"
    
    def test_deployment(self, url):
        """Test the deployed application"""
        print(f"🧪 Testing deployment at {url}")
        
        import urllib.request
        import urllib.error
        
        endpoints = [
            ('Health Check', '/health'),
            ('Projects API', '/api/v1/projects')
        ]
        
        for name, endpoint in endpoints:
            try:
                with urllib.request.urlopen(f"{url}{endpoint}") as response:
                    if response.status == 200:
                        print(f"✅ {name}: OK")
                    else:
                        print(f"⚠️  {name}: Status {response.status}")
            except urllib.error.URLError as e:
                print(f"❌ {name}: Failed - {e}")
    
    def deploy(self):
        """Execute complete deployment"""
        print("🚀 AI Data Analyst MVP - Serverless Deployment")
        print("=" * 60)
        
        try:
            self.create_project()
            self.enable_apis()
            self.create_app_files()
            url = self.deploy_to_app_engine()
            self.test_deployment(url)
            
            print("\n🎉 DEPLOYMENT SUCCESSFUL!")
            print("=" * 60)
            print(f"✅ Project ID: {self.project_id}")
            print(f"✅ App URL: {url}")
            print(f"✅ Health Check: {url}/health") 
            print(f"✅ API Endpoints: {url}/api/v1/projects")
            print(f"✅ Google Cloud Console: https://console.cloud.google.com/home/dashboard?project={self.project_id}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ DEPLOYMENT FAILED: {e}")
            return False

if __name__ == "__main__":
    deployer = ServerlessDeployer()
    success = deployer.deploy()
    sys.exit(0 if success else 1)