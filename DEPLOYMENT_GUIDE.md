# Full Stack Deployment Guide

**Project**: AI Data Analyst  
**Date**: October 30, 2025  
**Version**: 2.0.0-auth  
**Status**: Production Ready

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Deployment Targets](#deployment-targets)
3. [Local Development](#local-development)
4. [Docker Deployment](#docker-deployment)
5. [Google Cloud Run](#google-cloud-run)
6. [Heroku Deployment](#heroku-deployment)
7. [AWS Deployment](#aws-deployment)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- **Git** - For version control
- **Docker** - For containerized deployment
- **Node.js** (v18+) - For frontend
- **Python** (v3.9+) - For backend

### One-Command Deployment

```bash
# Make script executable
chmod +x deploy.sh

# Deploy locally (development)
./deploy.sh local

# Deploy with Docker
./deploy.sh docker

# Deploy to Google Cloud Run
./deploy.sh cloud-run

# Deploy to Heroku
./deploy.sh heroku

# Deploy to AWS
./deploy.sh aws
```

---

## Deployment Targets

### Local Development
**Best for**: Development, testing, debugging  
**Speed**: Instant  
**Cost**: Free  
**Command**: `./deploy.sh local`

### Docker
**Best for**: Consistent environments, CI/CD pipelines  
**Speed**: 5-10 minutes  
**Cost**: Free (self-hosted)  
**Command**: `./deploy.sh docker`

### Google Cloud Run
**Best for**: Serverless, auto-scaling, Google Cloud integration  
**Speed**: 10-15 minutes  
**Cost**: Pay-per-use ($0.00001389/GB-second)  
**Command**: `./deploy.sh cloud-run`

### Heroku
**Best for**: Quick deployment, GitHub integration  
**Speed**: 5 minutes  
**Cost**: $7-550/month depending on dyno type  
**Command**: `./deploy.sh heroku`

### AWS
**Best for**: Enterprise, full control, integration with AWS services  
**Speed**: 20-30 minutes  
**Cost**: Variable based on services used  
**Command**: `./deploy.sh aws`

---

## Local Development

### Setup

```bash
./deploy.sh local
```

This will:
- Create Python virtual environment (.venv)
- Install backend dependencies (Flask, JWT, bcrypt, etc.)
- Install frontend dependencies (React, Redux, Tailwind, etc.)
- Create configuration files (.env, .env.local)

### Running

**Terminal 1 - Backend**
```bash
cd /Users/swarnabale/Documents/Pradeep_Projects/Kaggle_test
source .venv/bin/activate
python main.py
# Backend running on http://localhost:8080
```

**Terminal 2 - Frontend**
```bash
cd /Users/swarnabale/Documents/Pradeep_Projects/Kaggle_test/frontend
npm run dev
# Frontend running on http://localhost:3001
```

**Terminal 3 - Optional: Run Tests**
```bash
npm test
```

### Access Application

- Frontend: http://localhost:3001
- Backend API: http://localhost:8080
- Backend Health: http://localhost:8080/health

### Configuration

**Backend** (.env)
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production
PORT=8080
MAX_STORAGE_PER_USER_MB=100
JWT_EXPIRATION_HOURS=24
```

**Frontend** (frontend/.env.local)
```env
VITE_API_URL=http://localhost:8080
VITE_APP_NAME=AI Data Analyst
VITE_ENVIRONMENT=development
```

---

## Docker Deployment

### Setup

```bash
./deploy.sh docker
```

This will:
- Create Dockerfile for backend
- Create Dockerfile for frontend
- Create docker-compose.yml
- Build Docker images
- Tag images with timestamp

### Docker Images

**Backend Image**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
EXPOSE 8080
CMD ["python", "main.py"]
```

**Frontend Image**
```dockerfile
# Build stage
FROM node:18-alpine as builder
# Frontend build...

# Runtime stage
FROM node:18-alpine
# Serve production build...
```

### Running with Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# View running containers
docker ps
```

### Docker Compose Services

```yaml
backend:
  - Port: 8080
  - Environment: FLASK_ENV=production
  - Volume: ./data:/app/data (persistent storage)
  - Auto-restart: unless-stopped

frontend:
  - Port: 3000
  - Environment: VITE_API_URL=http://backend:8080
  - Depends on: backend service
  - Auto-restart: unless-stopped
```

### Environment Variables

**Backend**
```bash
docker-compose exec backend env | grep FLASK
docker-compose exec backend env | grep SECRET
```

**Update Variables**
```bash
docker-compose down
# Edit docker-compose.yml
docker-compose up -d
```

### Data Persistence

```bash
# Data stored in ./data directory
ls -la data/
# - users.json (user accounts)
# - projects.json (user projects)
# - datasets.json (user datasets)

# Backup data
cp -r data/ data.backup_$(date +%Y%m%d_%H%M%S)/

# Restore data
cp -r data.backup_YYYYMMDD_HHMMSS/* data/
```

### Debugging

```bash
# View service logs
docker-compose logs backend
docker-compose logs frontend

# Follow logs in real-time
docker-compose logs -f backend

# View specific number of lines
docker-compose logs --tail=50 backend

# Inspect container
docker-compose exec backend sh
docker-compose exec frontend sh
```

---

## Google Cloud Run

### Prerequisites

1. Google Cloud Account with billing enabled
2. gcloud CLI installed
3. Docker installed (for building images)

### Setup

```bash
./deploy.sh cloud-run
```

You'll be prompted for:
- GCP Project ID
- GCP Region (default: us-central1)

### What Gets Created

1. **Artifact Registry** - Docker image repository
2. **Cloud Build** - Automated image building
3. **Cloud Run Services**:
   - `ai-data-analyst-backend` - Backend service
   - `ai-data-analyst-frontend` - Frontend service
4. **Service URLs** - Automatically generated

### Deployment Details

**Backend Service**
- Memory: 512MB
- Timeout: 540 seconds
- Concurrency: 80
- Environment: Production
- Scaling: 0 to auto (serverless)

**Frontend Service**
- Memory: 256MB
- Timeout: 300 seconds
- Concurrency: 80
- Environment: Production
- Scaling: 0 to auto (serverless)

### Configuration

```bash
# Update environment variables
gcloud run services update ai-data-analyst-backend \
  --update-env-vars SECRET_KEY=new-key

# View service details
gcloud run services describe ai-data-analyst-backend

# View logs
gcloud run services logs read ai-data-analyst-backend --limit=50

# Stream logs
gcloud run services logs read ai-data-analyst-backend --follow
```

### Costs

- **Request Processing**: $0.00001389 per GB-second
- **Storage (Artifact Registry)**: $0.10 per GB-month
- **Cloud Build**: $0.003 per build-minute
- **First 180,000 GB-seconds free per month** (~200 GB-seconds daily)

### Scale

```bash
# Auto-scale settings
gcloud run services update ai-data-analyst-backend \
  --min-instances 0 \
  --max-instances 100

# Set concurrency
gcloud run services update ai-data-analyst-backend \
  --concurrency 80
```

### Custom Domain

```bash
# Map custom domain
gcloud run services update ai-data-analyst-frontend \
  --update-env-vars VITE_API_URL=https://api.yourdomain.com

# Setup DNS
# In your domain registrar, create CNAME:
# frontend.yourdomain.com -> c.run.app
```

---

## Heroku Deployment

### Prerequisites

1. Heroku Account (free tier available)
2. Heroku CLI installed
3. Git installed

### Setup

```bash
./deploy.sh heroku
```

You'll be prompted for:
- Heroku app name

### What Gets Created

1. **Heroku App** - Remote hosting
2. **Procfile** - Process definition
3. **Environment Variables** - App configuration
4. **Git Remote** - heroku remote added

### Deployment Details

**Dyno Types** (choose based on needs)
- `free` - Free tier, sleeps after 30 min inactivity
- `hobby` - $7/month, always on
- `standard-1x` - $25/month, 512MB
- `performance-m` - $50/month, 2.5GB

### Configuration

```bash
# View environment variables
heroku config --app=your-app-name

# Set environment variables
heroku config:set --app=your-app-name SECRET_KEY=new-key

# View logs
heroku logs --app=your-app-name --tail

# Access shell
heroku run bash --app=your-app-name
```

### Database (PostgreSQL)

```bash
# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev --app=your-app-name

# View database URL
heroku config --app=your-app-name | grep DATABASE_URL
```

### File Storage

Heroku has **ephemeral filesystem** (files deleted on redeploy). For persistent storage:

```bash
# Option 1: AWS S3
heroku config:set --app=your-app-name AWS_ACCESS_KEY=...

# Option 2: Heroku PostgreSQL (recommended)
# All data stored in database instead of files
```

### Deployment

```bash
# Deploy from git
git push heroku main

# View deployment status
heroku releases --app=your-app-name

# Rollback if needed
heroku releases:rollback --app=your-app-name
```

### Scaling

```bash
# View dyno types
heroku dyno:type --app=your-app-name

# Scale up
heroku dyno:resize standard-1x --app=your-app-name

# Scale down
heroku dyno:resize free --app=your-app-name
```

---

## AWS Deployment

### Prerequisites

1. AWS Account with billing enabled
2. AWS CLI installed and configured
3. Docker installed
4. IAM permissions for ECR, ECS, ALB

### Setup

```bash
./deploy.sh aws
```

You'll be prompted for:
- AWS Region (default: us-east-1)
- ECR Repository name

### Architecture

```
                        ┌─────────────────┐
                        │  Route 53 DNS   │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │ Application     │
                        │ Load Balancer   │
                        └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    │                         │
            ┌───────▼────────┐      ┌────────▼───────┐
            │  ECS Cluster   │      │  ECS Cluster   │
            │  Backend Task  │      │ Frontend Task  │
            └────────┬───────┘      └────────┬───────┘
                     │                        │
            ┌────────▼──────────┐  ┌─────────▼────────┐
            │ RDS PostgreSQL    │  │  S3 Storage      │
            │ User Data         │  │  File Upload     │
            └───────────────────┘  └──────────────────┘
```

### Services Used

1. **ECR** - Container registry ($0.10/GB-month)
2. **ECS** - Container orchestration (free, pay for compute)
3. **EC2** - Compute instances ($0.015-0.05/hour)
4. **RDS** - Managed database ($15-100+/month)
5. **ALB** - Load balancer ($16/month + data)
6. **S3** - File storage ($0.023/GB-month)
7. **CloudWatch** - Monitoring (free tier)

### Deployment Steps

After running `./deploy.sh aws`:

1. **Create ECS Cluster**
   ```bash
   aws ecs create-cluster --cluster-name ai-data-analyst
   ```

2. **Create Task Definitions**
   - Backend task (512 CPU, 1024 memory)
   - Frontend task (256 CPU, 512 memory)

3. **Create Services**
   - Backend service (1-5 tasks)
   - Frontend service (1-5 tasks)

4. **Configure Load Balancer**
   - Health checks
   - Target groups
   - Routing rules

5. **Setup Auto Scaling**
   - Scale based on CPU/memory
   - Min/max task count

### Environment Variables

```bash
# Backend
AWS_REGION=us-east-1
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://...
S3_BUCKET=ai-data-analyst-bucket

# Frontend
VITE_API_URL=https://api.yourdomain.com
```

### RDS Database Setup

```bash
# Create database
aws rds create-db-instance \
  --db-instance-identifier ai-analyst-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password your-password

# Get connection string
aws rds describe-db-instances \
  --db-instance-identifier ai-analyst-db \
  --query 'DBInstances[0].Endpoint.Address'
```

### S3 File Storage

```bash
# Create bucket
aws s3 mb s3://ai-data-analyst-files

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ai-data-analyst-files \
  --versioning-configuration Status=Enabled

# Enable lifecycle rules for cost optimization
aws s3api put-bucket-lifecycle-configuration \
  --bucket ai-data-analyst-files \
  --lifecycle-configuration file://lifecycle.json
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Backend health
curl http://your-api.com/health

# Detailed health
curl http://your-api.com/api/v1/health/detailed

# Check API response time
time curl http://your-api.com/api/v1/projects
```

### Logs & Debugging

```bash
# Docker
docker-compose logs -f backend
docker-compose logs -f frontend

# Cloud Run
gcloud run services logs read ai-data-analyst-backend --limit=100

# Heroku
heroku logs -f --app=your-app-name

# AWS CloudWatch
aws logs tail /ecs/ai-data-analyst-backend --follow
```

### Database Backups

```bash
# Docker/Local
cp -r data/ data.backup_$(date +%Y%m%d_%H%M%S)/

# PostgreSQL
pg_dump postgresql://user:pass@host/db > backup.sql

# AWS RDS
aws rds create-db-snapshot \
  --db-instance-identifier ai-analyst-db \
  --db-snapshot-identifier ai-analyst-snapshot-$(date +%Y%m%d)
```

### Performance Monitoring

```bash
# View resource usage (Docker)
docker stats

# View build time
docker build --progress=plain -t image . 2>&1 | grep -E "^#|Successfully"

# Monitor startup time
time docker-compose up -d
```

### Updates & Patches

```bash
# Update dependencies
pip install --upgrade -r requirements.txt
npm update

# Rebuild containers
docker-compose build --no-cache
docker-compose up -d

# Restart services (zero-downtime)
docker-compose up -d --no-deps --build backend
```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Check port availability
lsof -i :8080

# Check dependencies
pip list | grep -E "Flask|JWT|bcrypt"

# Test backend locally
python -c "from main import app; print('OK')"
```

### Frontend Won't Connect to Backend

```bash
# Check backend is running
curl http://localhost:8080/health

# Check CORS is enabled (should be by default)
curl -H "Origin: http://localhost:3001" http://localhost:8080/health

# Check frontend .env
cat frontend/.env.local | grep VITE_API_URL

# Check browser console (F12)
# Look for CORS errors or failed requests
```

### Storage/Database Issues

```bash
# Check data directory exists
ls -la data/

# Check file permissions
chmod 644 data/*.json

# Reset database (development only)
rm -r data/
# Restart backend to recreate

# Backup before reset
cp -r data/ data.backup/
```

### Memory Issues

```bash
# Check resource usage
docker stats

# Increase memory limit
# In docker-compose.yml, add:
# deploy:
#   resources:
#     limits:
#       memory: 1G

docker-compose down && docker-compose up -d
```

### Authentication Issues

```bash
# Test registration
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User"
  }'

# Test login
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'

# Check JWT token expiration
python3 -c "
import jwt
import os
token = 'your-token-here'
try:
    decoded = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
    print('Valid token:', decoded)
except jwt.ExpiredSignatureError:
    print('Token expired')
except jwt.InvalidTokenError:
    print('Invalid token')
"
```

---

## Security Checklist

Before deploying to production:

- [ ] Change SECRET_KEY to random string
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS whitelist
- [ ] Enable database encryption
- [ ] Setup firewall rules
- [ ] Enable audit logging
- [ ] Setup rate limiting
- [ ] Setup backup strategy
- [ ] Enable monitoring/alerts
- [ ] Test security with tools
- [ ] Review environment variables
- [ ] Update all dependencies

---

## Performance Tuning

### Backend Optimization

```python
# main.py configuration
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
```

### Frontend Optimization

```bash
# Build optimization
npm run build -- --mode production

# Check bundle size
npm run build -- --mode production --report
```

### Database Optimization

```sql
-- Add indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_datasets_user_id ON datasets(user_id);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM projects WHERE user_id = ?;
```

---

## Support & Resources

- **Backend Docs**: [Flask Documentation](https://flask.palletsprojects.com/)
- **Frontend Docs**: [React Documentation](https://react.dev/)
- **Deployment**: [Deployment Best Practices](https://12factor.net/)
- **Docker**: [Docker Documentation](https://docs.docker.com/)
- **Cloud Run**: [Cloud Run Documentation](https://cloud.google.com/run/docs)

---

**Status**: ✅ Complete and Ready for Production  
**Last Updated**: October 30, 2025  
**Maintained By**: GitHub Copilot  
