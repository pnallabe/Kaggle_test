# AI Data Analyst — System Design (GCP-first)

**Purpose**: This document is the developer-facing system design for an AI Data Analyst product (Julius.ai-inspired) built primarily on Google Cloud Platform. It contains architecture, component responsibilities, data flows, API contracts, schemas, security/compliance, observability, deployment, cost/scale guidance, and an implementation rollout plan.

---

## 1. Executive summary

Build a multi-tenant, secure, conversational AI Data Analyst that lets teams connect datasets (CSV, BigQuery, Snowflake, Postgres, GCS), ask natural-language questions, receive reproducible analyses (tables, charts, EDA, models), and export/share results. The system is GCP-first: BigQuery for analytics, Vertex AI for embeddings/LLM/ML, Dataflow for ETL, Cloud Run for serverless compute, and Cloud SQL/Firestore for metadata.

Key principles:

* **Data locality**: keep analytics inside BigQuery/Vertex to minimize data movement.
* **Least privilege & auditability**: read-only connectors, audit logs, query dry-runs.
* **Cost control**: tiered answer quality; prefer embeddings + small models for previews; use BigQuery ML where possible.
* **Reproducibility**: all jobs produce an auditable plan and artifacts stored in GCS/BigQuery.

---

## 2. High-level architecture

Mermaid sequence (copy into a renderer if desired):

```mermaid
flowchart LR
  UI[React SPA] -->|HTTPS| APIGW[API Gateway / Cloud Run]
  APIGW --> Auth[Identity Platform]
  APIGW --> Cache[Memorystore (Redis)]
  APIGW --> Orchestrator[Cloud Run / Cloud Tasks / PubSub]
  Orchestrator --> BigQuery
  Orchestrator --> CloudRunWorker[Cloud Run workers]
  CloudRunWorker --> GCS
  CloudRunWorker --> VertexAI[Vertex AI (Embeddings/LLM/Training)]
  BigQuery --> VertexAI
  VertexAI --> MatchingEngine[Vertex Matching Engine]
  APIGW --> CloudSQL[Cloud SQL - metadata]
  GCS --> BigQuery
  Logs[Cloud Logging] --> Monitoring[Cloud Monitoring]
```

Components (brief):

* **Frontend**: React + TypeScript + Tailwind. Hosted on GCS + Cloud CDN.
* **API Layer**: Cloud Run containers (FastAPI) fronted by API Gateway / Cloud Endpoints. Uses Identity Platform.
* **Metadata store**: Cloud SQL (Postgres) for users, projects, RBAC, saved queries. Firestore for ephemeral session state if needed.
* **Analytics store**: BigQuery — canonical place for curated tables and query execution.
* **File/Artifact store**: Cloud Storage buckets per project (raw uploads, plot PNGs, CSV exports, notebooks).
* **ETL**: Dataflow (Apache Beam) for heavy/streaming transforms; Cloud Run for small/ad-hoc transforms.
* **Queueing / Tasks**: Pub/Sub + Cloud Tasks + Cloud Scheduler.
* **Embeddings & LLM**: Vertex AI Embeddings + Vertex Generative Models. Vector store: Vertex Matching Engine.
* **Analysis runtime**: Containerized Python (pandas, scikit-learn, xgboost, plotly) on Cloud Run for short tasks; Vertex AI Training for heavy model training (GPUs).
* **Monitoring & Security**: Cloud Monitoring, Cloud Logging, Secret Manager, Cloud KMS, DLP, VPC Service Controls.

---

## 3. Key flows & interactions

### 3.1. Query lifecycle (NL question -> result)

1. User submits NL query in UI.
2. UI calls API /jobs endpoint with user_id, project_id, dataset_refs, question.
3. API authenticates via Identity Platform and authorizes via Cloud SQL role mappings.
4. API checks cache (Redis). If cached answer exists and valid → return.
5. Otherwise, API initiates a job: publish message to Pub/Sub with job plan + metadata.
6. Worker pulls job: samples schema (dry-run) from BigQuery or reads small sample from GCS.
7. Worker uses Vertex Embeddings + Matching Engine to retrieve relevant schema/docs.
8. Worker calls Vertex LLM (prompt template) with sanitized context to produce a plan (steps and SQL/visualization specs).
9. Static analyzer validates proposed SQL/operations.
10. Worker executes plan: run BigQuery jobs for SQL; or run Cloud Run Python job for local transforms and visualization.
11. Artifacts stored in GCS; job metadata & audit written to Cloud SQL and optionally BigQuery audit dataset.
12. Frontend polls job status and renders results (charts, tables, explanation).

### 3.2. CSV ingestion flow

1. User uploads CSV via UI -> presigned URL to GCS.
2. Cloud Function triggers (or Cloud Run) that validates, converts to Parquet if needed, and writes metadata to Cloud SQL.
3. Dataflow pipeline optionally ingests the file into BigQuery (partitioned table) and writes schema and sample to metadata.

---

## 4. Component responsibilities & implementation notes

### 4.1. Frontend

* React + TypeScript. Components: Workspace list, Data Connectors, Query console, Notebook history, Visualizer, Model trainer.
* Authentication: OAuth via Identity Platform; support Google Workspace SSO.
* Caching: local caching for job previews.
* File uploads: use signed URLs from API (
  `/upload-url`) to GCS.

### 4.2. API (Cloud Run)

* Endpoints (examples):

  * `POST /api/v1/jobs` — submit analysis job (body: project_id, dataset_refs, question, preferred_model, options)
  * `GET /api/v1/jobs/{job_id}` — poll job status
  * `GET /api/v1/artifacts/{artifact_id}` — retrieve CSV/PNG/JSON
  * `POST /api/v1/connectors` — add data connector
  * `GET /api/v1/projects/{id}/schema` — list tables/columns
* Auth: verify JWT from Identity Platform; check Cloud SQL RBAC table.
* Rate-limits & usage quotas enforced here.

### 4.3. Workers / Analysis runtime

* Cloud Run services that execute the plan. Runs in sandboxed container with CPU & memory limits and timeout.
* Use environment variables to inject credentials (via Secret Manager) with least privilege.
* Key libraries: pandas, pyarrow, google-cloud-bigquery, google-cloud-storage, scikit-learn, xgboost, plotly.
* For SQL plans: use BigQuery dry-run to estimate cost before execution.

### 4.4. BigQuery usage patterns

* Promote all uploaded/ingested tables to a curated dataset per project. Use partitioning & clustering.
* Use BigQuery ML (BQML) for lightweight models (logistic regression, XGBoost) to reduce data egress and cost.
* Use BigQuery INFORMATION_SCHEMA and `__TABLES__` for schema discovery.

### 4.5. Vertex AI

* Use Vertex Embeddings to vectorize schema docs and sample rows. Store vectors in Matching Engine.
* Use Vertex Generative Models for plan generation and explanation. Keep prompt context minimal and sanitized.
* Use Vertex Model Monitoring for production models.

### 4.6. Metadata & audit

* Cloud SQL schema (high-level):

  * users (id, email, workspace_id, role)
  * projects (id, name, owner_id, billing_tier)
  * connectors (id, project_id, type, config_encrypted)
  * jobs (id, project_id, user_id, status, plan_json, started_at, finished_at)
  * artifacts (id, job_id, type, gcs_path, size)
  * access_logs (id, user_id, action, target, timestamp, ip)
* Export detailed logs to BigQuery for analytics.

---

## 5. Data model and API contracts (sample)

### 5.1. Job submission payload (POST /api/v1/jobs)

```json
{
  "project_id": "proj_123",
  "user_id": "user_abc",
  "dataset_refs": [
    {"type":"bigquery","dataset":"proj.dataset.table"},
    {"type":"gcs","path":"gs://bucket/path/file.csv"}
  ],
  "question": "What are the top drivers of churn in the last 12 months?",
  "options": {"max_rows": 100000, "model_tier":"preview"}
}
```

### 5.2. Job result (GET /api/v1/jobs/{job_id})

```json
{
  "id":"job_123",
  "status":"finished",
  "plan": {"steps": [...], "sql_queries": [...]},
  "results": {"tables":[{"name":"driver_table","artifact_id":"art_1"}], "charts":[{"type":"bar","artifact_id":"art_2"}]},
  "explanation":"...",
  "artifacts":[{"id":"art_1","gcs_path":"gs://.../drivers.csv"}]
}
```

---

## 6. Security, privacy, and compliance

* **Authentication**: Identity Platform + OAuth/SAML federation.
* **Authorization**: RBAC stored in Cloud SQL, enforced by API. Use Cloud IAM for infra-level access.
* **Encryption**: GCS/CMEK (Cloud KMS); Cloud SQL with CMEK optional.
* **Secrets**: Secret Manager for DB/connector creds.
* **PII / DLP**: Use Cloud DLP to detect/mask PII before sending content to Vertex LLMs or storing into embeddings. Flag datasets with PII in metadata.
* **Network**: VPC with private access to BigQuery and private IP for Cloud SQL. Use VPC Service Controls to limit exfiltration.
* **Audit & logging**: Cloud Logging (audit logs), export to BigQuery for retention.
* **Data residency**: choose GCP region for all resources as per customer requirement.

Sensitive operation protections:

* SQL generation: do not auto-run destructive SQL; only generate and show to user (dry-run). Enforce read-only DB credentials.
* LLM output filtering: apply regex/PII checks to LLM outputs; redact sensitive values.

---

## 7. Observability & SLOs

Metrics to monitor:

* API latency (p95 < 500ms for simple ops)
* Job completion time (median & p95)
* LLM token usage & cost per job
* BigQuery bytes scanned per job
* Error rate (5xx) < 0.5%

Tools: Cloud Monitoring dashboards, error reports, alerting on unusual spikes in BigQuery scan cost or LLM calls.

---

## 8. CI/CD & release process

* **Repo structure**: `frontend/`, `api/`, `workers/`, `infra/` (terraform), `dataflow/`.
* **Build pipeline**: Cloud Build or GitHub Actions; build containers, run unit tests, push to Artifact Registry.
* **Infra**: Terraform modules for network, GCS, BigQuery dataset, Cloud SQL, Cloud Run services, Pub/Sub topics, Vertex resources.
* **Deploy**: Canary deploy to staging then promote to prod. Use TrafficSplit on Cloud Run if desired.
* **Image signing**: Artifact Registry + Binary Authorization for production.

---

## 9. Cost-management & scaling guidance

* Prefer BigQuery for heavy aggregations. Use query dry-runs to estimate bytes scanned and enforce limits per job.
* Offer a "preview" mode that uses embeddings + cached results instead of full LLM runs.
* Use BigQuery slot reservations for predictable performance if enterprise.
* Use autoscaled Cloud Run for interactive workloads; use Vertex Training with GPU pools only for heavy jobs.

---

## 10. Roadmap & milestones (developer-oriented)

**MVP (Phase 0)**

* CSV upload -> GCS + ingest to BigQuery.
* Frontend query box + POST /jobs to create job.
* Basic worker: sample schema + simple EDA (counts, missing, histograms) using Cloud Run.
* Store artifacts in GCS and job metadata in Cloud SQL.

**Phase 1**

* Vertex Embeddings for schema & small RAG.
* Vertex Generative Models for plan generation (preview tier).
* BigQuery execution for SQL plans; static SQL validator + dry-run.
* Notebook history and export.

**Phase 2**

* Models (BQML + Vertex Training); SHAP/explainability via Vertex Explainable AI.
* Connectors: Cloud SQL (Postgres), Snowflake (federated), external JDBC.
* Scheduled reports (Cloud Scheduler + Cloud Tasks).

**Phase 3 (enterprise)**

* Private VPC, CMEK, VPC-SC enforcement.
* Single-tenant deployment pattern (dedicated GKE/Cloud Run clusters).
* SSO + advanced audit retention.

---

## 11. Acceptance criteria (examples)

* User can upload CSV, ingest to BigQuery, and run a natural language EDA job returning a chart and explanation.
* Jobs produce a verifiable `plan_json` and write artifacts to GCS with proper ACLs.
* All data movement is logged and auditable; PII detection flags datasets correctly.
* API authentication works via Identity Platform; role-based access is enforced.

---

## 12. Next steps for implementation

1. Create Terraform skeleton for starter resources (GCS, BigQuery dataset, Cloud SQL, Pub/Sub, Cloud Run service) — minimal infra.
2. Implement CSV upload + ingestion pipeline (Cloud Run + Dataflow job + BigQuery load).
3. Implement API `POST /jobs` and a basic worker that runs EDA and stores artifacts.
4. Integrate Vertex Embeddings + LLM in a preview mode to synthesize simple plans.
5. Add monitoring, alerts, and cost controls (BigQuery dry-run limits, LLM call caps).

---

## 13. Appendix

* **Helpful libraries**: `google-cloud-bigquery`, `google-cloud-storage`, `apache-beam[gcp]`, `vertex-ai`, `pandas`, `pyarrow`, `scikit-learn`, `xgboost`, `plotly`.
* **Recommended regions**: pick one multi-region per customer (e.g., `us-central1` or `us-east1`) for BigQuery and Vertex.
* **Dev environment**: use small BigQuery sandbox for development; use service accounts with minimal scopes.

---

*Document prepared as a developer-oriented system design. If you want, I can generate:*

* *Terraform skeleton for the starter stack,*
* *A concrete Dataflow+BigQuery ingestion pipeline (Apache Beam),* or
* *An OpenAPI spec for the API endpoints listed.*

Say which one you want next and I will create it in this workspace.
