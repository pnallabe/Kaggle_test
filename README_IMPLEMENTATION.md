# AI Data Analyst — GCP Implementation

An enterprise-grade conversational AI data analyst platform built on Google Cloud Platform, enabling teams to ask natural-language questions about their data and receive reproducible analyses, visualizations, and insights.

## Project Structure

```
├── api/                          # FastAPI backend service
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration and settings
│   │   ├── auth.py              # Authentication and authorization
│   │   ├── database.py          # Database models and operations
│   │   └── routers/             # API endpoint definitions
│   │       ├── jobs.py          # Job submission and polling
│   │       ├── artifacts.py     # Artifact retrieval
│   │       ├── connectors.py    # Data connector management
│   │       ├── schema.py        # Schema and dataset endpoints
│   │       └── health.py        # Health checks
│   ├── tests/                   # Unit and integration tests
│   ├── main.py                  # Application entry point
│   ├── requirements.txt          # Python dependencies
│   └── Dockerfile               # Container configuration
│
├── infra/                        # Terraform infrastructure
│   ├── main.tf                  # Main infrastructure definitions
│   ├── variables.tf             # Input variables
│   ├── outputs.tf               # Output values
│   ├── terraform.tfvars.example # Example environment config
│   └── schema.sql               # Database initialization script
│
├── frontend/                     # React UI (placeholder)
│   └── README.md
│
├── workers/                      # Cloud Run worker services
│   └── README.md
│
├── cloudbuild.yaml              # CI/CD pipeline configuration
├── PHASE_1_SETUP.md             # Detailed setup guide
├── .env.local.example           # Environment variables template
└── README.md                    # This file

```

## Key Features (Phase 1)

✅ **Infrastructure as Code**: Complete GCP setup via Terraform
✅ **REST API**: FastAPI-based backend with OpenAPI documentation
✅ **Authentication**: Google Identity Platform with JWT validation
✅ **Database**: PostgreSQL metadata store with schema management
✅ **Cloud Storage**: GCS integration for artifacts
✅ **Pub/Sub**: Async job queue for worker orchestration
✅ **Monitoring**: Cloud Logging and Monitoring setup
✅ **CI/CD**: Cloud Build pipeline with automated testing and deployment

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│                    (GCS + Cloud CDN)                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cloud Run (API)                              │
│              (FastAPI + Uvicorn)                                │
│         • Authentication (Identity Platform)                    │
│         • Authorization (RBAC)                                  │
│         • Rate limiting                                          │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    ┌─────────┐          ┌──────────┐         ┌────────────┐
    │Cloud SQL│          │BigQuery  │         │Cloud       │
    │         │          │          │         │Storage     │
    │Metadata │          │Analytics │         │Artifacts   │
    └─────────┘          └──────────┘         └────────────┘
         │
         ├──────────┬──────────────┬──────────────┐
         │          │              │              │
         ▼          ▼              ▼              ▼
    ┌────────┐ ┌────────┐   ┌──────────┐   ┌─────────┐
    │Pub/Sub │ │Redis   │   │Secret    │   │Cloud    │
    │Job     │ │Cache   │   │Manager   │   │KMS      │
    │Queue   │ │        │   │          │   │Encryption│
    └────────┘ └────────┘   └──────────┘   └─────────┘
         │
         ▼
    ┌─────────────────────────────────────────────┐
    │     Cloud Run Workers                       │
    │  • SQL generation & execution               │
    │  • Visualization creation                   │
    │  • Data transformation                      │
    └─────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- GCP Project with billing enabled
- `gcloud` CLI configured
- `terraform` >= 1.0
- Docker
- Python 3.11+

### Local Development

1. **Clone repository**
   ```bash
   git clone <repository>
   cd Kaggle_test
   ```

2. **Setup Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   cd api
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your settings
   ```

4. **Run API locally**
   ```bash
   uvicorn main:app --reload
   ```

5. **Access documentation**
   - Swagger UI: http://localhost:8080/docs
   - ReDoc: http://localhost:8080/redoc

### GCP Deployment

See [PHASE_1_SETUP.md](./PHASE_1_SETUP.md) for comprehensive deployment guide.

**Quick deployment:**
```bash
cd infra
terraform init -backend-config="bucket=YOUR_BUCKET"
terraform plan -var-file="terraform.tfvars"
terraform apply
```

## API Endpoints (Phase 1)

### Health & Status
- `GET /health` — Service health check
- `GET /ready` — Readiness probe

### Jobs
- `POST /api/v1/jobs` — Submit analysis job
- `GET /api/v1/jobs/{job_id}` — Get job status
- `GET /api/v1/jobs?project_id=X` — List jobs
- `DELETE /api/v1/jobs/{job_id}` — Cancel job

### Artifacts
- `GET /api/v1/artifacts/{artifact_id}` — Retrieve artifact
- `GET /api/v1/artifacts?job_id=X` — List artifacts
- `DELETE /api/v1/artifacts/{artifact_id}` — Delete artifact

### Data Connectors
- `POST /api/v1/connectors` — Create connector
- `GET /api/v1/connectors?project_id=X` — List connectors
- `GET /api/v1/connectors/{connector_id}` — Get connector
- `DELETE /api/v1/connectors/{connector_id}` — Delete connector
- `POST /api/v1/connectors/{connector_id}/test` — Test connector

### Schema
- `GET /api/v1/projects/{project_id}/schema` — Get schema
- `GET /api/v1/projects/{project_id}/datasets` — List datasets
- `GET /api/v1/projects/{project_id}/datasets/{dataset_id}/columns` — Get columns
- `GET /api/v1/projects/{project_id}/datasets/{dataset_id}/sample` — Get sample data

## Database Schema

PostgreSQL tables created during setup:
- `users` — User accounts and workspace mapping
- `projects` — Projects and metadata
- `project_access` — RBAC and permissions
- `connectors` — Data source configurations
- `jobs` — Analysis job records
- `artifacts` — Job output artifacts
- `access_logs` — Audit trail
- `saved_queries` — Notebook history

See [infra/schema.sql](./infra/schema.sql) for complete schema.

## Security Features

- **Authentication**: OAuth 2.0 via Google Identity Platform
- **Authorization**: Role-based access control (RBAC)
- **Encryption**: Cloud KMS for data encryption
- **Secret Management**: Secret Manager for credentials
- **Network**: VPC with private Cloud SQL and Redis
- **Audit**: Cloud Logging and BigQuery audit dataset
- **DLP**: Cloud DLP integration for PII detection

## Monitoring and Alerting

- Cloud Monitoring dashboards
- Custom alerts for error rates, latency, resource usage
- Cloud Logging for centralized logs
- BigQuery for audit analytics

## Testing

```bash
# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Test specific module
pytest tests/test_auth.py -v
```

## CI/CD Pipeline

Cloud Build pipeline (`cloudbuild.yaml`) includes:
1. Run unit tests
2. Build Docker image
3. Push to Artifact Registry
4. Deploy to Cloud Run (staging)
5. Canary deploy to production

Trigger on:
- Push to `main` branch (production)
- Push to `develop` branch (staging)
- Pull requests (testing)

## Configuration

Environment variables (see `.env.local.example`):

| Variable | Purpose | Example |
|----------|---------|---------|
| `GCP_PROJECT_ID` | GCP project | `my-project-123` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` |
| `REDIS_HOST` | Redis host | `10.0.0.5` |
| `BQ_ANALYTICS_DATASET` | BigQuery dataset | `analytics_prod` |
| `GCS_ARTIFACTS_BUCKET` | GCS bucket for output | `my-artifacts-bucket` |
| `JWT_AUDIENCE` | OAuth client ID | `xxx.apps.googleusercontent.com` |

## Troubleshooting

### Cloud SQL Connection Failed
```bash
# Verify instance is running
gcloud sql instances list

# Check network connectivity
gcloud sql connect INSTANCE_NAME --user=postgres
```

### Cloud Run Deploy Issues
```bash
# Check service status
gcloud run services describe ai-data-analyst

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

### Authentication Errors
```bash
# Verify OAuth configuration
gcloud identity-aware-proxy oauth-brands list

# Test JWT validation
curl -H "Authorization: Bearer TOKEN" http://localhost:8080/health
```

## Performance Targets (SLOs)

- API latency (p95): < 500ms
- Job completion (median): < 30s
- Availability: 99.5%
- Error rate: < 0.5%

## Cost Optimization

- BigQuery: Use query dry-runs, slot reservations
- Cloud Run: Auto-scaling with min instances = 0
- Storage: Lifecycle policies for old artifacts
- Caching: Redis for frequently accessed results

## Roadmap

**Phase 1** (Complete): Infrastructure & API
**Phase 2**: Data Ingestion & ETL
**Phase 3**: Conversational Querying (LLM integration)
**Phase 4**: Visualization & Insights
**Phase 5**: Security & Multi-tenancy
**Phase 6**: Optimization & Launch

## Contributing

1. Create feature branch: `git checkout -b feature/name`
2. Make changes and test: `pytest tests/`
3. Commit: `git commit -am "Description"`
4. Push: `git push origin feature/name`
5. Create Pull Request

## License

Proprietary - AI Data Analyst Platform

## Support

For issues or questions:
- Documentation: [PHASE_1_SETUP.md](./PHASE_1_SETUP.md)
- System Design: [AIDataAnalyst_System_Design.md](./AIDataAnalyst_System_Design.md)
- Roadmap: [AIDataAnalyst_delivery_map.md](./AIDataAnalyst_delivery_map.md)

## Contact

Project Owner: [Your Team]
Technical Lead: [Your Name]

---

**Last Updated**: October 2025
**Version**: 1.0.0
