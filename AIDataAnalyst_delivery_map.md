# AI Data Analyst — Delivery Roadmap (GCP-First)

## 1. Overview

This roadmap outlines the phased delivery plan for developing and deploying the AI Data Analyst platform built primarily on Google Cloud Platform (GCP). It defines timelines, objectives, deliverables, and dependencies across six key phases.

---

## 2. Timeline Summary

| Phase | Focus Area               | Duration    | Key Outcome                                            |
| ----- | ------------------------ | ----------- | ------------------------------------------------------ |
| 1     | Foundations              | Weeks 1–4   | Core infrastructure, authentication, and API setup     |
| 2     | Data Ingestion & ETL     | Weeks 5–8   | Automated ingestion and transformation pipelines       |
| 3     | Conversational Querying  | Weeks 9–12  | LLM-based natural language querying and SQL generation |
| 4     | Visualization & Insights | Weeks 13–16 | Visual analytics and narrative generation engine       |
| 5     | Security & Multi-Tenancy | Weeks 17–20 | Secure, scalable multi-tenant architecture             |
| 6     | Optimization & Launch    | Weeks 21–24 | Performance tuning, documentation, and MVP release     |

---

## 3. Phase Details

### Phase 1: Foundations (Weeks 1–4)

**Objective:** Establish baseline infrastructure and API framework.

* Set up GCP project, IAM roles, and VPC networking.
* Deploy Cloud Run API service (FastAPI backend).
* Configure Cloud SQL for metadata and GCS for storage.
* Integrate Google Identity Platform for authentication.
* Build CI/CD pipeline using Cloud Build + Artifact Registry.

**Milestone:** Authenticated API & UI prototype with GCP deployment.

---

### Phase 2: Data Ingestion & ETL (Weeks 5–8)

**Objective:** Automate ingestion and transformation workflows.

* Implement Dataflow pipelines for CSV/Parquet ingestion.
* Integrate schema inference and validation logic.
* Create Cloud Composer DAG for batch orchestration.
* Record dataset metadata in Cloud SQL.
* Provide API endpoint for dataset uploads and refresh.

**Milestone:** End-to-end dataset ingestion from upload to BigQuery.

---

### Phase 3: Conversational Querying (Weeks 9–12)

**Objective:** Enable natural language-driven data exploration.

* Integrate Vertex AI Generative Model for text-to-SQL.
* Generate embeddings using Vertex AI Embeddings API.
* Set up Matching Engine for RAG-based retrieval.
* Implement BigQuery dry-run and safe execution validation.
* Expose query endpoints in backend API.

**Milestone:** Conversational query interface operational with safe SQL generation.

---

### Phase 4: Visualization & Insight Generation (Weeks 13–16)

**Objective:** Add automated visualization and narrative capabilities.

* Implement visualization API (Plotly + Chart templates).
* Integrate Looker Studio for advanced dashboards.
* Generate text-based insights using Vertex LLMs.
* Add caching (Memorystore) for repeated queries.

**Milestone:** Dynamic charts and AI-generated narratives available to users.

---

### Phase 5: Security & Multi-Tenancy (Weeks 17–20)

**Objective:** Secure system for multiple tenants and ensure compliance.

* Implement tenant isolation (IAM + dataset-level access).
* Add VPC Service Controls and Secret Manager.
* Integrate Cloud Logging, Monitoring, and alerts.
* Configure billing metering and audit trail.

**Milestone:** Fully secure and monitored multi-tenant environment.

---

### Phase 6: Optimization & Launch (Weeks 21–24)

**Objective:** Finalize product for MVP release.

* Conduct load testing and performance tuning.
* Optimize BigQuery slot usage and Cloud Run autoscaling.
* Finalize documentation, onboarding guide, and training.
* Deploy MVP to selected customers and gather feedback.

**Milestone:** Public beta launch with feedback collection loop.

---

## 4. Dependencies & Parallelization

* **Parallelizable Work:** Frontend dev, LLM prompt design, and CI/CD setup.
* **Critical Dependencies:** Data ingestion must precede conversational querying.
* **LLM Fine-tuning:** Starts after ingestion pipeline is stable.
* **Visualization:** Can start during Phase 3 if mock data is available.

---

## 5. Resource Requirements

| Role              | Responsibility                     | % Allocation |
| ----------------- | ---------------------------------- | ------------ |
| Product Manager   | Roadmap ownership, sprint planning | 50%          |
| Cloud Architect   | GCP infra, IAM, networking         | 50%          |
| Backend Engineer  | API, ingestion, orchestration      | 100%         |
| ML Engineer       | LLM & embeddings integration       | 75%          |
| Frontend Engineer | UI, visualization                  | 75%          |
| DevOps Engineer   | CI/CD, monitoring                  | 50%          |
| QA Engineer       | Test automation & validation       | 50%          |

---

## 6. Success Metrics

* 95% uptime in testing environments.
* Query execution latency < 5 seconds for standard datasets.
* 90% accuracy in natural language intent recognition.
* MVP delivered by Week 24.

---

## 7. Post-MVP Enhancements

* Voice-based query interface (Dialogflow CX).
* Google Sheets and Looker connectors.
* Fine-tuned domain LLMs.
* Self-service workspace provisioning.
* Enterprise private deployment via GKE.

---

**Document Owner:** Program Management Office
**Version:** v1.0
**Last Updated:** October 2025
