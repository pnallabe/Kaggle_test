# AI Data Analyst - API Documentation

## 📚 REST API Reference

The AI Data Analyst API provides programmatic access to all platform capabilities including data connections, query execution, visualization generation, and tenant management.

**Base URL**: `https://api.aidataanalyst.com/v1`  
**Authentication**: Bearer Token (JWT)  
**Content Type**: `application/json`

## 🔐 Authentication

### Getting Started

All API requests require authentication using a Bearer token. Obtain your API key from the platform dashboard under Settings → API Keys.

```bash
curl -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     https://api.aidataanalyst.com/v1/health
```

### Authentication Methods

#### 1. API Key Authentication
```http
Authorization: Bearer aida_live_1234567890abcdef...
```

#### 2. JWT Token Authentication (for user sessions)
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 3. Service Account Authentication
```http
Authorization: Bearer aida_service_abcdef1234567890...
```

## 📊 Core Endpoints

### Health Check

Check API status and connectivity.

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-29T10:30:00Z",
  "version": "1.0.0",
  "region": "us-central1"
}
```

### Authentication

#### Login
```http
POST /auth/login
```

**Request Body**:
```json
{
  "email": "user@company.com",
  "password": "secure_password",
  "tenant_domain": "company.com"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "refresh_token_here",
  "expires_in": 3600,
  "user": {
    "id": "user_123",
    "email": "user@company.com",
    "name": "John Doe",
    "role": "analyst"
  },
  "tenant": {
    "id": "tenant_456",
    "name": "Acme Corporation",
    "domain": "company.com"
  }
}
```

#### Refresh Token
```http
POST /auth/refresh
```

**Request Body**:
```json
{
  "refresh_token": "refresh_token_here"
}
```

## 💼 Project Management

### List Projects
```http
GET /projects
```

**Query Parameters**:
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)
- `sort` (optional): Sort field (default: created_at)

**Response**:
```json
{
  "projects": [
    {
      "id": "proj_123",
      "name": "Sales Analytics",
      "description": "Customer and revenue analysis",
      "created_at": "2025-10-01T10:00:00Z",
      "updated_at": "2025-10-29T09:00:00Z",
      "owner_id": "user_123",
      "datasets_count": 5,
      "queries_count": 147
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### Create Project
```http
POST /projects
```

**Request Body**:
```json
{
  "name": "Marketing Analytics",
  "description": "Campaign performance and ROI analysis",
  "visibility": "private"
}
```

### Get Project Details
```http
GET /projects/{project_id}
```

**Response**:
```json
{
  "id": "proj_123",
  "name": "Sales Analytics",
  "description": "Customer and revenue analysis",
  "created_at": "2025-10-01T10:00:00Z",
  "updated_at": "2025-10-29T09:00:00Z",
  "owner": {
    "id": "user_123",
    "name": "John Doe",
    "email": "john@company.com"
  },
  "datasets": [
    {
      "id": "dataset_456",
      "name": "customer_data",
      "type": "bigquery",
      "table_id": "company.analytics.customers",
      "rows": 50000,
      "columns": 25
    }
  ],
  "permissions": {
    "can_edit": true,
    "can_delete": true,
    "can_share": true
  }
}
```

## 📁 Data Source Management

### List Data Sources
```http
GET /projects/{project_id}/datasources
```

**Response**:
```json
{
  "datasources": [
    {
      "id": "ds_789",
      "name": "Customer Database",
      "type": "postgresql",
      "status": "connected",
      "last_sync": "2025-10-29T08:00:00Z",
      "tables": [
        {
          "name": "customers",
          "rows": 50000,
          "columns": 25
        },
        {
          "name": "orders", 
          "rows": 125000,
          "columns": 15
        }
      ]
    }
  ]
}
```

### Add Data Source
```http
POST /projects/{project_id}/datasources
```

**Request Body (PostgreSQL)**:
```json
{
  "name": "Production Database",
  "type": "postgresql",
  "config": {
    "host": "db.company.com",
    "port": 5432,
    "database": "analytics",
    "username": "readonly_user",
    "password": "encrypted_password",
    "ssl_mode": "require"
  },
  "sync_schedule": "0 */6 * * *"
}
```

**Request Body (CSV Upload)**:
```json
{
  "name": "Sales Data",
  "type": "csv",
  "config": {
    "file_url": "https://presigned-url.com/sales_data.csv",
    "has_header": true,
    "delimiter": ",",
    "encoding": "utf-8"
  }
}
```

**Request Body (BigQuery)**:
```json
{
  "name": "Analytics Warehouse",
  "type": "bigquery",
  "config": {
    "project_id": "company-analytics",
    "dataset_id": "production",
    "service_account_key": "base64_encoded_key"
  }
}
```

### Get Data Source Schema
```http
GET /projects/{project_id}/datasources/{datasource_id}/schema
```

**Response**:
```json
{
  "datasource_id": "ds_789",
  "tables": [
    {
      "name": "customers",
      "columns": [
        {
          "name": "customer_id",
          "type": "INTEGER",
          "nullable": false,
          "primary_key": true
        },
        {
          "name": "email",
          "type": "STRING",
          "nullable": false
        },
        {
          "name": "created_at",
          "type": "TIMESTAMP",
          "nullable": false
        },
        {
          "name": "total_spent",
          "type": "FLOAT",
          "nullable": true
        }
      ],
      "row_count": 50000,
      "sample_data": [
        {
          "customer_id": 1,
          "email": "customer1@example.com",
          "created_at": "2024-01-15T10:30:00Z",
          "total_spent": 1250.50
        }
      ]
    }
  ]
}
```

## 🤖 Query Execution

### Submit Analysis Job
```http
POST /projects/{project_id}/jobs
```

**Request Body**:
```json
{
  "question": "What are the top 10 customers by total spending?",
  "datasource_refs": [
    {
      "datasource_id": "ds_789",
      "tables": ["customers", "orders"]
    }
  ],
  "options": {
    "max_rows": 10000,
    "include_explanation": true,
    "generate_visualization": true,
    "model_tier": "standard"
  }
}
```

**Response**:
```json
{
  "job_id": "job_abc123",
  "status": "queued",
  "created_at": "2025-10-29T10:30:00Z",
  "estimated_completion": "2025-10-29T10:31:00Z",
  "question": "What are the top 10 customers by total spending?",
  "options": {
    "max_rows": 10000,
    "include_explanation": true,
    "generate_visualization": true,
    "model_tier": "standard"
  }
}
```

### Get Job Status
```http
GET /jobs/{job_id}
```

**Response (In Progress)**:
```json
{
  "job_id": "job_abc123",
  "status": "running",
  "progress": 0.6,
  "created_at": "2025-10-29T10:30:00Z",
  "started_at": "2025-10-29T10:30:15Z",
  "current_step": "executing_query",
  "steps": [
    {
      "name": "analyzing_question",
      "status": "completed",
      "duration_ms": 1200
    },
    {
      "name": "generating_sql",
      "status": "completed", 
      "duration_ms": 800
    },
    {
      "name": "executing_query",
      "status": "running",
      "started_at": "2025-10-29T10:30:45Z"
    }
  ]
}
```

**Response (Completed)**:
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "created_at": "2025-10-29T10:30:00Z",
  "started_at": "2025-10-29T10:30:15Z",
  "completed_at": "2025-10-29T10:31:20Z",
  "duration_ms": 65000,
  "question": "What are the top 10 customers by total spending?",
  "results": {
    "summary": {
      "rows_returned": 10,
      "total_rows_analyzed": 50000,
      "query_cost": 0.025
    },
    "data": {
      "columns": [
        {"name": "customer_id", "type": "integer"},
        {"name": "customer_name", "type": "string"},
        {"name": "total_spending", "type": "float"}
      ],
      "rows": [
        [1001, "Acme Corp", 45230.50],
        [2045, "TechStart Inc", 38910.25],
        [3891, "Global Solutions", 35470.80]
      ]
    },
    "visualization": {
      "type": "bar_chart",
      "title": "Top 10 Customers by Total Spending",
      "artifact_id": "viz_def456"
    },
    "explanation": "Analysis shows the top 10 customers based on total spending across all orders. Acme Corp leads with $45,230.50 in total purchases.",
    "sql_query": "SELECT customer_id, customer_name, SUM(order_total) as total_spending FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY customer_id, customer_name ORDER BY total_spending DESC LIMIT 10",
    "artifacts": [
      {
        "id": "data_abc123",
        "type": "csv",
        "url": "/artifacts/data_abc123"
      },
      {
        "id": "viz_def456", 
        "type": "png",
        "url": "/artifacts/viz_def456"
      }
    ]
  }
}
```

### List Jobs
```http
GET /projects/{project_id}/jobs
```

**Query Parameters**:
- `status` (optional): Filter by status (queued, running, completed, failed)
- `limit` (optional): Number of results (default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Response**:
```json
{
  "jobs": [
    {
      "job_id": "job_abc123",
      "status": "completed",
      "question": "What are the top 10 customers by total spending?",
      "created_at": "2025-10-29T10:30:00Z",
      "completed_at": "2025-10-29T10:31:20Z",
      "duration_ms": 65000,
      "cost": 0.025
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

## 📈 Artifacts & Downloads

### Get Artifact
```http
GET /artifacts/{artifact_id}
```

**Response**: Binary data (CSV, PNG, JSON, etc.)

**Headers**:
```
Content-Type: image/png
Content-Disposition: attachment; filename=visualization.png
Content-Length: 145632
```

### List Artifacts
```http
GET /jobs/{job_id}/artifacts
```

**Response**:
```json
{
  "artifacts": [
    {
      "id": "data_abc123",
      "type": "csv",
      "filename": "top_customers.csv",
      "size_bytes": 2048,
      "created_at": "2025-10-29T10:31:20Z",
      "download_url": "/artifacts/data_abc123"
    },
    {
      "id": "viz_def456",
      "type": "png", 
      "filename": "customer_spending_chart.png",
      "size_bytes": 145632,
      "created_at": "2025-10-29T10:31:22Z",
      "download_url": "/artifacts/viz_def456"
    }
  ]
}
```

## 📊 Dashboards

### Create Dashboard
```http
POST /projects/{project_id}/dashboards
```

**Request Body**:
```json
{
  "name": "Sales Performance Dashboard",
  "description": "Key metrics for sales team",
  "layout": {
    "grid_size": 12,
    "widgets": [
      {
        "id": "widget_1",
        "type": "metric",
        "title": "Total Revenue",
        "position": {"x": 0, "y": 0, "w": 3, "h": 2},
        "job_id": "job_revenue_123"
      },
      {
        "id": "widget_2", 
        "type": "chart",
        "title": "Monthly Trends",
        "position": {"x": 3, "y": 0, "w": 9, "h": 4},
        "job_id": "job_trends_456"
      }
    ]
  },
  "refresh_interval": 3600,
  "visibility": "team"
}
```

### Get Dashboard
```http
GET /dashboards/{dashboard_id}
```

**Response**:
```json
{
  "id": "dash_789",
  "name": "Sales Performance Dashboard",
  "description": "Key metrics for sales team",
  "created_at": "2025-10-29T09:00:00Z",
  "updated_at": "2025-10-29T10:00:00Z",
  "owner": {
    "id": "user_123",
    "name": "John Doe"
  },
  "layout": {
    "grid_size": 12,
    "widgets": [
      {
        "id": "widget_1",
        "type": "metric",
        "title": "Total Revenue",
        "position": {"x": 0, "y": 0, "w": 3, "h": 2},
        "data": {
          "value": 1250000,
          "change": 0.15,
          "period": "month"
        }
      }
    ]
  },
  "refresh_interval": 3600,
  "last_refreshed": "2025-10-29T10:00:00Z"
}
```

## 👥 User Management

### List Users (Admin)
```http
GET /admin/users
```

**Response**:
```json
{
  "users": [
    {
      "id": "user_123",
      "email": "john@company.com",
      "name": "John Doe",
      "role": "analyst",
      "status": "active",
      "last_login": "2025-10-29T09:30:00Z",
      "created_at": "2025-09-15T14:20:00Z"
    }
  ],
  "total": 1
}
```

### Create User (Admin)
```http
POST /admin/users
```

**Request Body**:
```json
{
  "email": "newuser@company.com",
  "name": "Jane Smith",
  "role": "analyst",
  "send_invitation": true,
  "projects": ["proj_123", "proj_456"]
}
```

### Update User Role (Admin)
```http
PATCH /admin/users/{user_id}
```

**Request Body**:
```json
{
  "role": "admin",
  "status": "active"
}
```

## 🏢 Tenant Management

### Get Tenant Info
```http
GET /tenant
```

**Response**:
```json
{
  "id": "tenant_456",
  "name": "Acme Corporation", 
  "domain": "company.com",
  "plan": "enterprise",
  "created_at": "2025-09-01T10:00:00Z",
  "settings": {
    "max_users": 500,
    "max_projects": 100,
    "data_retention_days": 365,
    "api_rate_limit": 1000
  },
  "usage": {
    "active_users": 47,
    "total_projects": 12,
    "queries_this_month": 2847,
    "storage_used_gb": 15.7
  },
  "compliance": {
    "frameworks": ["SOC2", "GDPR"],
    "data_residency": "US"
  }
}
```

### Update Tenant Settings (Admin)
```http
PATCH /admin/tenant
```

**Request Body**:
```json
{
  "settings": {
    "max_users": 750,
    "api_rate_limit": 1500
  }
}
```

## 📊 Analytics & Usage

### Get Usage Statistics
```http
GET /analytics/usage
```

**Query Parameters**:
- `start_date`: Start date (ISO 8601)
- `end_date`: End date (ISO 8601)
- `granularity`: hour, day, week, month

**Response**:
```json
{
  "period": {
    "start_date": "2025-10-01T00:00:00Z",
    "end_date": "2025-10-29T23:59:59Z",
    "granularity": "day"
  },
  "metrics": {
    "total_queries": 2847,
    "unique_users": 47,
    "total_cost": 142.35,
    "avg_query_time_ms": 4250
  },
  "daily_breakdown": [
    {
      "date": "2025-10-01",
      "queries": 95,
      "unique_users": 12,
      "cost": 4.75
    }
  ]
}
```

### Get Performance Metrics
```http
GET /analytics/performance
```

**Response**:
```json
{
  "current_performance": {
    "avg_response_time_ms": 850,
    "p95_response_time_ms": 2100,
    "error_rate": 0.002,
    "uptime_percentage": 99.97
  },
  "trends": {
    "response_time_trend": "improving",
    "query_volume_trend": "increasing",
    "user_satisfaction": 4.6
  }
}
```

## ❌ Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "The request is invalid or malformed",
    "details": "Missing required field: question",
    "request_id": "req_abc123xyz",
    "timestamp": "2025-10-29T10:30:00Z"
  }
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `authentication_required` | 401 | Missing or invalid authentication token |
| `insufficient_permissions` | 403 | User lacks required permissions |
| `resource_not_found` | 404 | Requested resource does not exist |
| `invalid_request` | 400 | Request format or parameters are invalid |
| `rate_limit_exceeded` | 429 | Too many requests in time window |
| `internal_error` | 500 | Unexpected server error |
| `service_unavailable` | 503 | Service temporarily unavailable |
| `datasource_unavailable` | 502 | Cannot connect to data source |
| `query_timeout` | 408 | Query execution exceeded time limit |
| `quota_exceeded` | 429 | Account quota or limit exceeded |

### Error Handling Best Practices

1. **Always check status codes** before processing responses
2. **Implement exponential backoff** for retries
3. **Log request_id** for support ticket correlation
4. **Handle rate limits** gracefully with delays
5. **Validate requests** before sending to avoid 400 errors

## 🔄 Rate Limits

### Default Limits

- **Standard Plan**: 100 requests per minute
- **Professional Plan**: 500 requests per minute  
- **Enterprise Plan**: 2000 requests per minute

### Rate Limit Headers

Response headers indicate current usage:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1635504000
Retry-After: 60
```

### Handling Rate Limits

When you exceed rate limits, you'll receive a 429 response:

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded",
    "details": "100 requests per minute limit reached",
    "retry_after": 60
  }
}
```

## 📘 SDK & Libraries

### Official SDKs

#### Python SDK
```bash
pip install aidataanalyst-python
```

```python
from aidataanalyst import Client

client = Client(api_key="your-api-key")

# Submit a query
job = client.query(
    project_id="proj_123",
    question="What are our top products?",
    datasources=["ds_789"]
)

# Wait for results
results = job.wait_for_completion()
print(results.data)
```

#### JavaScript SDK
```bash
npm install @aidataanalyst/sdk
```

```javascript
import { AIDataAnalyst } from '@aidataanalyst/sdk';

const client = new AIDataAnalyst({
  apiKey: 'your-api-key'
});

// Submit a query
const job = await client.query({
  projectId: 'proj_123',
  question: 'What are our top products?',
  datasources: ['ds_789']
});

// Get results
const results = await job.waitForCompletion();
console.log(results.data);
```

### Webhook Integration

Configure webhooks to receive real-time notifications:

```http
POST /webhooks
```

**Request Body**:
```json
{
  "url": "https://your-app.com/webhooks/aidataanalyst",
  "events": ["job.completed", "job.failed", "datasource.updated"],
  "secret": "webhook_secret_key"
}
```

**Webhook Payload Example**:
```json
{
  "event": "job.completed",
  "timestamp": "2025-10-29T10:31:20Z",
  "data": {
    "job_id": "job_abc123",
    "project_id": "proj_123",
    "status": "completed",
    "duration_ms": 65000,
    "cost": 0.025
  }
}
```

## 🚀 Getting Started

### Quick Start

1. **Get API Key**: Generate from dashboard Settings → API Keys
2. **Test Connection**: Call `/health` endpoint
3. **Create Project**: Use `/projects` to set up workspace
4. **Add Data Source**: Connect your first dataset  
5. **Submit Query**: Ask your first question
6. **Get Results**: Download data and visualizations

### Sample Integration

```bash
# 1. Test API connection
curl -H "Authorization: Bearer your-api-key" \
     https://api.aidataanalyst.com/v1/health

# 2. Create a project
curl -X POST \
     -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"name":"My First Project","description":"Testing the API"}' \
     https://api.aidataanalyst.com/v1/projects

# 3. Submit a query
curl -X POST \
     -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"question":"Show me a summary of my data","datasource_refs":[{"datasource_id":"ds_123"}]}' \
     https://api.aidataanalyst.com/v1/projects/proj_456/jobs
```

---

## 📞 Support

### API Support
- **Email**: api-support@aidataanalyst.com
- **Documentation**: https://docs.aidataanalyst.com
- **Status Page**: https://status.aidataanalyst.com
- **Community**: https://community.aidataanalyst.com

### Rate Limit Increases
Contact sales@aidataanalyst.com for higher rate limits or custom enterprise configurations.

---

**API Version**: v1  
**Last Updated**: October 2025  
**Document ID**: AIDA-API-001