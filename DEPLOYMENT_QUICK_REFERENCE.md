# Deployment Quick Reference

**AI Data Analyst - Full Stack Deployment**  
**Version**: 2.0.0-auth  
**Updated**: October 30, 2025

---

## One-Command Deployments

```bash
# Local Development (instant)
./deploy.sh local

# Docker (5-10 minutes)
./deploy.sh docker

# Google Cloud Run (10-15 minutes)
./deploy.sh cloud-run

# Heroku (5 minutes)
./deploy.sh heroku

# AWS (20-30 minutes)
./deploy.sh aws
```

---

## Platform Comparison

| Feature | Local | Docker | Cloud Run | Heroku | AWS |
|---------|-------|--------|-----------|--------|-----|
| **Setup Time** | Instant | 5-10 min | 10-15 min | 5 min | 20-30 min |
| **Cost** | Free | Free* | $0.0001/GB-s | $7-550/mo | Variable |
| **Auto-Scale** | No | Manual | Yes | Limited | Yes |
| **Database** | JSON | JSON | JSON | Optional | RDS |
| **Storage** | Local | Docker Vol | GCS | Ephemeral | S3 |
| **Best For** | Dev | Testing | Production | Quick Deploy | Enterprise |

*Docker cost depends on hosting platform

---

## Local Development

```bash
# Setup
./deploy.sh local

# Terminal 1 - Backend
source .venv/bin/activate
python main.py
# http://localhost:8080

# Terminal 2 - Frontend
cd frontend && npm run dev
# http://localhost:3001

# Terminal 3 - Optional Tests
npm test
```

**Files Created**:
- `.venv/` - Python virtual environment
- `frontend/node_modules/` - Frontend dependencies
- `.env` - Backend config
- `frontend/.env.local` - Frontend config

---

## Docker Deployment

```bash
# Setup
./deploy.sh docker

# Start
docker-compose up -d

# View Logs
docker-compose logs -f

# Stop
docker-compose down

# URLs
# Frontend: http://localhost:3000
# Backend: http://localhost:8080
```

**Files Created**:
- `Dockerfile.backend` - Backend image
- `Dockerfile.frontend` - Frontend image
- `docker-compose.yml` - Services config

**Containers**:
- `backend` (port 8080, 512MB RAM)
- `frontend` (port 3000, 256MB RAM)

---

## Google Cloud Run

```bash
# Prerequisites
gcloud auth login
gcloud config set project PROJECT_ID

# Deploy
./deploy.sh cloud-run
# Prompts for Project ID and Region

# View Services
gcloud run services list

# View Logs
gcloud run services logs read SERVICE_NAME --limit=50

# Update Config
gcloud run services update SERVICE_NAME \
  --update-env-vars KEY=VALUE
```

**Services Created**:
- `ai-data-analyst-backend` (512MB)
- `ai-data-analyst-frontend` (256MB)

**Costs** (~$5-15/month typical usage):
- First 180,000 GB-seconds free per month
- $0.00001389 per GB-second after

**Custom Domain**:
```bash
gcloud run services update SERVICE_NAME \
  --set-cloudsql-instances=... (if using Cloud SQL)
```

---

## Heroku Deployment

```bash
# Prerequisites
heroku login

# Deploy
./deploy.sh heroku
# Prompts for app name

# Deploy Updates
git push heroku main

# View Logs
heroku logs -f --app=APP_NAME

# View Config
heroku config --app=APP_NAME

# Scale Dynos
heroku dyno:resize standard-1x --app=APP_NAME
```

**App Created**:
- `APP_NAME` - Application

**Dyno Types**:
- `free` - Free (sleeps after 30 min)
- `hobby` - $7/month
- `standard-1x` - $25/month

**Add PostgreSQL**:
```bash
heroku addons:create heroku-postgresql:hobby-dev
```

---

## AWS Deployment

```bash
# Prerequisites
aws configure  # Set credentials
docker login   # Login to Docker

# Deploy
./deploy.sh aws
# Prompts for region and repo name

# View Images
aws ecr describe-repositories

# View Services
aws ecs list-services --cluster CLUSTER_NAME

# View Logs
aws logs tail /ecs/SERVICE_NAME --follow
```

**Services Created**:
- ECR repositories (backend, frontend)
- ECS cluster
- Task definitions
- Services

**Next Steps**:
1. Create RDS database (PostgreSQL)
2. Create S3 bucket (file storage)
3. Setup ALB (load balancer)
4. Configure Route 53 (DNS)
5. Setup auto-scaling

---

## Environment Variables

### Backend (.env)

```env
FLASK_ENV=production|development
SECRET_KEY=random-secret-key-256-bits
PORT=8080
MAX_STORAGE_PER_USER_MB=100
JWT_EXPIRATION_HOURS=24
```

### Frontend (.env.local or .env.production)

```env
VITE_API_URL=https://api.yourdomain.com
VITE_APP_NAME=AI Data Analyst
VITE_ENVIRONMENT=production
```

---

## Common Commands

### Docker

```bash
# Build
docker build -t my-image .

# Run
docker run -p 8080:8080 my-image

# Compose
docker-compose up -d
docker-compose logs -f
docker-compose down

# Cleanup
docker system prune -a
```

### gcloud (Cloud Run)

```bash
# Deploy
gcloud run deploy SERVICE --image IMAGE

# Update
gcloud run services update SERVICE --update-env-vars KEY=VALUE

# Delete
gcloud run services delete SERVICE
```

### Heroku

```bash
# Deploy
git push heroku main

# Scale
heroku ps:scale web=2

# Restart
heroku restart

# Shell
heroku run bash
```

### AWS

```bash
# Push to ECR
aws ecr get-login-password | docker login ...
docker tag image:latest REPO/image:latest
docker push REPO/image:latest

# Update ECS Service
aws ecs update-service \
  --cluster CLUSTER \
  --service SERVICE \
  --force-new-deployment
```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Check dependencies
pip list

# Test import
python3 -c "from main import app; print('OK')"
```

### Frontend Won't Connect

```bash
# Check backend running
curl http://localhost:8080/health

# Check .env
cat frontend/.env.local

# Check CORS
curl -H "Origin: http://localhost" http://localhost:8080/health
```

### Storage Issues

```bash
# Check data directory
ls -la data/

# Backup data
cp -r data/ data.backup/

# Reset (dev only)
rm -r data/
```

### Authentication Issues

```bash
# Test registration
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"pass123","name":"Test"}'

# Test login
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"pass123"}'
```

---

## Performance Tips

1. **Use Docker** for consistent environments
2. **Use Cloud Run** for auto-scaling and cost efficiency
3. **Use CDN** for static assets
4. **Use Database** instead of JSON files for production
5. **Enable Caching** for API responses
6. **Monitor** resource usage and optimize

---

## Production Checklist

- [ ] Use SECRET_KEY (random 256-bit string)
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS properly
- [ ] Enable database encryption
- [ ] Setup monitoring/alerts
- [ ] Enable audit logging
- [ ] Setup backup strategy
- [ ] Test security
- [ ] Update dependencies
- [ ] Configure rate limiting

---

## Support

- **Documentation**: See `DEPLOYMENT_GUIDE.md`
- **Issues**: Check troubleshooting section
- **Questions**: Review platform-specific docs
- **Help**: Run `./deploy.sh --help` (future feature)

---

**Status**: ✅ Production Ready  
**Last Updated**: October 30, 2025  
**Maintained By**: GitHub Copilot

