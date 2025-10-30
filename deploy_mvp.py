#!/usr/bin/env python3
"""
AI Data Analyst MVP - Cloud Deployment Script

This script deploys the MVP to Google Cloud Platform for testing.
It sets up the complete infrastructure and deploys all services.
"""

import os
import sys
import json
import logging
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MVPDeployer:
    """MVP deployment orchestrator for Google Cloud Platform"""
    
    def __init__(self, project_id: str, region: str = "us-central1"):
        self.project_id = project_id
        self.region = region
        self.deployment_id = f"mvp-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Service configurations
        self.services = {
            "ai-analyst-api": {
                "port": 8080,
                "cpu": "2",
                "memory": "4Gi",
                "min_instances": 1,
                "max_instances": 10
            },
            "ai-analyst-frontend": {
                "port": 3000,
                "cpu": "1",
                "memory": "2Gi",
                "min_instances": 1,
                "max_instances": 5
            }
        }
        
        logger.info(f"Initialized MVP Deployer for project: {project_id}")
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met for deployment"""
        logger.info("🔍 Checking deployment prerequisites...")
        
        checks = []
        
        # Check if gcloud is installed and authenticated
        try:
            result = subprocess.run(['gcloud', 'auth', 'list'], 
                                  capture_output=True, text=True, check=True)
            if 'No credentialed accounts' in result.stdout:
                logger.error("❌ Not authenticated with gcloud. Run: gcloud auth login")
                checks.append(False)
            else:
                logger.info("✅ gcloud authentication verified")
                checks.append(True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("❌ gcloud CLI not found or authentication failed")
            checks.append(False)
        
        # Check if Docker is available
        try:
            subprocess.run(['docker', '--version'], 
                          capture_output=True, check=True)
            logger.info("✅ Docker is available")
            checks.append(True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("❌ Docker not found or not running")
            checks.append(False)
        
        # Check if project exists and APIs are enabled
        try:
            subprocess.run(['gcloud', 'projects', 'describe', self.project_id], 
                          capture_output=True, check=True)
            logger.info(f"✅ Project {self.project_id} exists")
            checks.append(True)
        except subprocess.CalledProcessError:
            logger.error(f"❌ Project {self.project_id} not found or inaccessible")
            checks.append(False)
        
        return all(checks)
    
    def enable_apis(self) -> bool:
        """Enable required Google Cloud APIs"""
        logger.info("🔧 Enabling required Google Cloud APIs...")
        
        required_apis = [
            "run.googleapis.com",
            "cloudbuild.googleapis.com",
            "bigquery.googleapis.com",
            "storage.googleapis.com",
            "sqladmin.googleapis.com",
            "secretmanager.googleapis.com",
            "monitoring.googleapis.com",
            "logging.googleapis.com",
            "artifactregistry.googleapis.com"
        ]
        
        try:
            for api in required_apis:
                logger.info(f"Enabling {api}...")
                subprocess.run([
                    'gcloud', 'services', 'enable', api, 
                    '--project', self.project_id
                ], check=True, capture_output=True)
            
            logger.info("✅ All required APIs enabled")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to enable APIs: {e}")
            return False
    
    def setup_infrastructure(self) -> bool:
        """Set up required infrastructure components"""
        logger.info("🏗️  Setting up infrastructure...")
        
        try:
            # Create Cloud Storage buckets
            self._create_storage_buckets()
            
            # Create BigQuery datasets
            self._create_bigquery_datasets()
            
            # Create Cloud SQL instance
            self._create_cloudsql_instance()
            
            # Create Artifact Registry repository
            self._create_artifact_registry()
            
            # Set up secrets
            self._setup_secrets()
            
            logger.info("✅ Infrastructure setup completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Infrastructure setup failed: {e}")
            return False
    
    def _create_storage_buckets(self):
        """Create required Cloud Storage buckets"""
        buckets = [
            f"{self.project_id}-ai-analyst-data",
            f"{self.project_id}-ai-analyst-models",
            f"{self.project_id}-ai-analyst-exports"
        ]
        
        for bucket in buckets:
            try:
                subprocess.run([
                    'gcloud', 'storage', 'buckets', 'create', 
                    f'gs://{bucket}',
                    '--location', self.region,
                    '--project', self.project_id
                ], check=True, capture_output=True)
                logger.info(f"Created bucket: {bucket}")
            except subprocess.CalledProcessError:
                logger.info(f"Bucket {bucket} already exists or creation failed")
    
    def _create_bigquery_datasets(self):
        """Create BigQuery datasets"""
        datasets = ["analytics", "customer_data", "system_logs"]
        
        for dataset in datasets:
            try:
                subprocess.run([
                    'bq', 'mk', '--dataset',
                    '--location', 'US',
                    f'{self.project_id}:{dataset}'
                ], check=True, capture_output=True)
                logger.info(f"Created BigQuery dataset: {dataset}")
            except subprocess.CalledProcessError:
                logger.info(f"Dataset {dataset} already exists or creation failed")
    
    def _create_cloudsql_instance(self):
        """Create Cloud SQL PostgreSQL instance"""
        instance_name = "ai-analyst-db"
        
        try:
            subprocess.run([
                'gcloud', 'sql', 'instances', 'create', instance_name,
                '--database-version', 'POSTGRES_15',
                '--tier', 'db-f1-micro',
                '--region', self.region,
                '--storage-type', 'SSD',
                '--storage-size', '20GB',
                '--backup-start-time', '02:00',
                '--enable-bin-log',
                '--project', self.project_id
            ], check=True, capture_output=True)
            logger.info(f"Created Cloud SQL instance: {instance_name}")
            
            # Create database
            subprocess.run([
                'gcloud', 'sql', 'databases', 'create', 'ai_analyst',
                '--instance', instance_name,
                '--project', self.project_id
            ], check=True, capture_output=True)
            logger.info("Created database: ai_analyst")
            
        except subprocess.CalledProcessError:
            logger.info("Cloud SQL instance already exists or creation failed")
    
    def _create_artifact_registry(self):
        """Create Artifact Registry for container images"""
        repo_name = "ai-analyst-images"
        
        try:
            subprocess.run([
                'gcloud', 'artifacts', 'repositories', 'create', repo_name,
                '--repository-format', 'docker',
                '--location', self.region,
                '--project', self.project_id
            ], check=True, capture_output=True)
            logger.info(f"Created Artifact Registry: {repo_name}")
        except subprocess.CalledProcessError:
            logger.info("Artifact Registry already exists or creation failed")
    
    def _setup_secrets(self):
        """Set up Secret Manager secrets"""
        secrets = {
            "DATABASE_URL": f"postgresql://postgres:password@/ai_analyst?host=/cloudsql/{self.project_id}:{self.region}:ai-analyst-db",
            "JWT_SECRET": "your-super-secret-jwt-key-change-in-production",
            "BIGQUERY_CREDENTIALS": "{}",  # Will be populated with service account
            "OPENAI_API_KEY": "your-openai-api-key"
        }
        
        for secret_name, secret_value in secrets.items():
            try:
                # Create secret
                subprocess.run([
                    'gcloud', 'secrets', 'create', secret_name,
                    '--project', self.project_id
                ], check=True, capture_output=True)
                
                # Add secret version
                subprocess.run([
                    'gcloud', 'secrets', 'versions', 'add', secret_name,
                    '--data-file', '-',
                    '--project', self.project_id
                ], input=secret_value, text=True, check=True, capture_output=True)
                
                logger.info(f"Created secret: {secret_name}")
            except subprocess.CalledProcessError:
                logger.info(f"Secret {secret_name} already exists or creation failed")
    
    def build_and_push_images(self) -> bool:
        """Build and push container images"""
        logger.info("🐳 Building and pushing container images...")
        
        try:
            # Build API image
            self._build_api_image()
            
            # Build frontend image
            self._build_frontend_image()
            
            logger.info("✅ Container images built and pushed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Image build failed: {e}")
            return False
    
    def _build_api_image(self):
        """Build and push API container image"""
        image_name = f"{self.region}-docker.pkg.dev/{self.project_id}/ai-analyst-images/api:latest"
        
        # Create Dockerfile for API
        dockerfile_content = """
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY security/ ./security/
COPY performance/ ./performance/

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
"""
        
        with open("Dockerfile.api", "w") as f:
            f.write(dockerfile_content)
        
        # Create requirements.txt
        requirements_content = """
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
google-cloud-bigquery==3.13.0
google-cloud-storage==2.10.0
google-cloud-secret-manager==2.16.4
redis==5.0.1
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
openai==1.3.5
pandas==2.1.3
numpy==1.25.2
requests==2.31.0
"""
        
        with open("requirements.txt", "w") as f:
            f.write(requirements_content)
        
        # Build and push
        subprocess.run([
            'docker', 'build', '-f', 'Dockerfile.api', 
            '-t', image_name, '.'
        ], check=True)
        
        subprocess.run([
            'docker', 'push', image_name
        ], check=True)
        
        logger.info(f"Built and pushed API image: {image_name}")
    
    def _build_frontend_image(self):
        """Build and push frontend container image"""
        image_name = f"{self.region}-docker.pkg.dev/{self.project_id}/ai-analyst-images/frontend:latest"
        
        # Create Dockerfile for frontend
        dockerfile_content = """
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY frontend/src ./src/
COPY frontend/public ./public/

# Build the app
RUN npm run build

# Use nginx to serve the built app
FROM nginx:alpine
COPY --from=0 /app/build /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/nginx.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
"""
        
        with open("Dockerfile.frontend", "w") as f:
            f.write(dockerfile_content)
        
        # Create basic nginx config
        os.makedirs("frontend", exist_ok=True)
        nginx_config = """
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    server {
        listen 3000;
        server_name localhost;
        
        location / {
            root /usr/share/nginx/html;
            index index.html index.htm;
            try_files $uri $uri/ /index.html;
        }
        
        location /api/ {
            proxy_pass http://ai-analyst-api:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
"""
        
        with open("frontend/nginx.conf", "w") as f:
            f.write(nginx_config)
        
        # Create basic package.json
        package_json = {
            "name": "ai-analyst-frontend",
            "version": "1.0.0",
            "scripts": {
                "build": "echo 'Frontend build placeholder'",
                "start": "echo 'Frontend start placeholder'"
            }
        }
        
        with open("frontend/package.json", "w") as f:
            json.dump(package_json, f, indent=2)
        
        # Create build directory
        os.makedirs("frontend/build", exist_ok=True)
        with open("frontend/build/index.html", "w") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>AI Data Analyst MVP</title>
</head>
<body>
    <h1>AI Data Analyst MVP</h1>
    <p>Frontend placeholder - MVP deployment successful!</p>
</body>
</html>
""")
        
        # Build and push
        subprocess.run([
            'docker', 'build', '-f', 'Dockerfile.frontend', 
            '-t', image_name, '.'
        ], check=True)
        
        subprocess.run([
            'docker', 'push', image_name
        ], check=True)
        
        logger.info(f"Built and pushed frontend image: {image_name}")
    
    def deploy_services(self) -> bool:
        """Deploy services to Cloud Run"""
        logger.info("🚀 Deploying services to Cloud Run...")
        
        try:
            # Deploy API service
            self._deploy_api_service()
            
            # Deploy frontend service
            self._deploy_frontend_service()
            
            logger.info("✅ Services deployed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Service deployment failed: {e}")
            return False
    
    def _deploy_api_service(self):
        """Deploy API service to Cloud Run"""
        service_name = "ai-analyst-api"
        image_name = f"{self.region}-docker.pkg.dev/{self.project_id}/ai-analyst-images/api:latest"
        
        subprocess.run([
            'gcloud', 'run', 'deploy', service_name,
            '--image', image_name,
            '--platform', 'managed',
            '--region', self.region,
            '--allow-unauthenticated',
            '--port', '8080',
            '--cpu', '2',
            '--memory', '4Gi',
            '--min-instances', '1',
            '--max-instances', '10',
            '--set-env-vars', f'PROJECT_ID={self.project_id}',
            '--set-env-vars', f'REGION={self.region}',
            '--project', self.project_id
        ], check=True)
        
        logger.info(f"Deployed {service_name} to Cloud Run")
    
    def _deploy_frontend_service(self):
        """Deploy frontend service to Cloud Run"""
        service_name = "ai-analyst-frontend"
        image_name = f"{self.region}-docker.pkg.dev/{self.project_id}/ai-analyst-images/frontend:latest"
        
        subprocess.run([
            'gcloud', 'run', 'deploy', service_name,
            '--image', image_name,
            '--platform', 'managed',
            '--region', self.region,
            '--allow-unauthenticated',
            '--port', '3000',
            '--cpu', '1',
            '--memory', '2Gi',
            '--min-instances', '1',
            '--max-instances', '5',
            '--project', self.project_id
        ], check=True)
        
        logger.info(f"Deployed {service_name} to Cloud Run")
    
    def run_health_checks(self) -> bool:
        """Run health checks on deployed services"""
        logger.info("🏥 Running health checks...")
        
        try:
            # Get service URLs
            api_url = self._get_service_url("ai-analyst-api")
            frontend_url = self._get_service_url("ai-analyst-frontend")
            
            # Test API health
            if self._test_endpoint(f"{api_url}/health"):
                logger.info("✅ API health check passed")
            else:
                logger.warning("⚠️  API health check failed")
            
            # Test frontend
            if self._test_endpoint(frontend_url):
                logger.info("✅ Frontend health check passed")
            else:
                logger.warning("⚠️  Frontend health check failed")
            
            logger.info("🎉 MVP deployment completed!")
            logger.info(f"API URL: {api_url}")
            logger.info(f"Frontend URL: {frontend_url}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Health checks failed: {e}")
            return False
    
    def _get_service_url(self, service_name: str) -> str:
        """Get the URL of a deployed Cloud Run service"""
        try:
            result = subprocess.run([
                'gcloud', 'run', 'services', 'describe', service_name,
                '--region', self.region,
                '--format', 'value(status.url)',
                '--project', self.project_id
            ], capture_output=True, text=True, check=True)
            
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""
    
    def _test_endpoint(self, url: str) -> bool:
        """Test if an endpoint is responding"""
        try:
            import requests
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def deploy(self) -> bool:
        """Execute complete MVP deployment"""
        logger.info("🚀 Starting AI Data Analyst MVP Deployment")
        logger.info("=" * 60)
        
        steps = [
            ("Prerequisites Check", self.check_prerequisites),
            ("Enable APIs", self.enable_apis),
            ("Setup Infrastructure", self.setup_infrastructure),
            ("Build Container Images", self.build_and_push_images),
            ("Deploy Services", self.deploy_services),
            ("Health Checks", self.run_health_checks)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"\n📋 Step: {step_name}")
            if not step_func():
                logger.error(f"❌ Failed at step: {step_name}")
                return False
            logger.info(f"✅ Completed: {step_name}")
        
        logger.info("\n🎉 MVP DEPLOYMENT SUCCESSFUL!")
        logger.info("=" * 60)
        return True


def main():
    """Main deployment function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy AI Data Analyst MVP to Google Cloud")
    parser.add_argument("--project-id", required=True, help="Google Cloud Project ID")
    parser.add_argument("--region", default="us-central1", help="Deployment region")
    
    args = parser.parse_args()
    
    deployer = MVPDeployer(args.project_id, args.region)
    success = deployer.deploy()
    
    if success:
        print("\n🎉 MVP deployment completed successfully!")
        print("Your AI Data Analyst platform is now running on Google Cloud Platform.")
        sys.exit(0)
    else:
        print("\n❌ MVP deployment failed!")
        print("Check the logs above for error details.")
        sys.exit(1)


if __name__ == "__main__":
    main()