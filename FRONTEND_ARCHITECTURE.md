# Frontend Architecture & Integration Guide

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER BROWSER                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          React Frontend (Vite + TypeScript)              │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │         Router (React Router v6)                  │ │  │
│  │  │                                                    │ │  │
│  │  │  ┌──────────────┐  ┌──────────────┐              │ │  │
│  │  │  │  Dashboard   │  │Query Console │              │ │  │
│  │  │  │    Page      │  │    Page      │              │ │  │
│  │  │  └──────────────┘  └──────────────┘              │ │  │
│  │  │                                                    │ │  │
│  │  │  ┌──────────────┐  ┌──────────────┐              │ │  │
│  │  │  │   Dataset    │  │  NotFound    │              │ │  │
│  │  │  │   Manager    │  │    Page      │              │ │  │
│  │  │  └──────────────┘  └──────────────┘              │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │       Redux Store (State Management)               │ │  │
│  │  │                                                    │ │  │
│  │  │  ┌──────────────┐  ┌──────────────┐              │ │  │
│  │  │  │  Projects    │  │   Datasets   │              │ │  │
│  │  │  │   Slice      │  │    Slice     │              │ │  │
│  │  │  └──────────────┘  └──────────────┘              │ │  │
│  │  │                                                    │ │  │
│  │  │  ┌──────────────┐                                │ │  │
│  │  │  │    Jobs      │                                │ │  │
│  │  │  │    Slice     │                                │ │  │
│  │  │  └──────────────┘                                │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │         API Service (Axios)                        │ │  │
│  │  │                                                    │ │  │
│  │  │  - HTTP Client                                    │ │  │
│  │  │  - Interceptors (Auth, Errors)                    │ │  │
│  │  │  - Job Polling                                    │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │       UI Component Library                         │ │  │
│  │  │                                                    │ │  │
│  │  │  Button • Card • Input • Textarea • DataTable      │ │  │
│  │  │  Alert • Toast • Badge • Loader • Skeleton         │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │        Styling Layer                                      │  │
│  │  - Tailwind CSS                                           │  │
│  │  - Dark Mode Support                                      │  │
│  │  - Responsive Design (Mobile/Tablet/Desktop)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         │ HTTP Requests (Axios)
         │ Bearer Token Authentication
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND API (Flask/Cloud Run)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  GET  /api/v1/projects          - List projects                │
│  POST /api/v1/jobs              - Submit query jobs            │
│  GET  /api/v1/jobs/:id          - Get job status               │
│  GET  /api/v1/datasets          - List datasets                │
│  POST /api/v1/datasets          - Upload datasets              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         │ BigQuery, PostgreSQL, Salesforce
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              DATA SOURCES                                        │
├─────────────────────────────────────────────────────────────────┤
│  - Google BigQuery                                              │
│  - PostgreSQL Databases                                         │
│  - Salesforce                                                   │
│  - Google Analytics                                             │
│  - Cloud Storage (GCS)                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Component Hierarchy

```
App
├── BrowserRouter
│   ├── Routes
│   │   └── Layout
│   │       ├── Navbar
│   │       │   ├── Notifications
│   │       │   ├── Theme Toggle
│   │       │   └── Profile Menu
│   │       ├── Sidebar
│   │       │   ├── Navigation
│   │       │   ├── Projects List
│   │       │   └── Settings
│   │       └── Main Content
│   │           ├── Dashboard
│   │           │   ├── Stats Cards
│   │           │   │   ├── Active Projects
│   │           │   │   ├── Data Sources
│   │           │   │   └── Last Updated
│   │           │   └── Projects Grid
│   │           │
│   │           ├── QueryConsole
│   │           │   ├── Query Input (Textarea)
│   │           │   ├── Dataset Selector
│   │           │   ├── Submit Button
│   │           │   └── Results Panel
│   │           │       ├── Job Status
│   │           │       ├── Progress Bar
│   │           │       └── Insights
│   │           │
│   │           ├── DatasetManager
│   │           │   ├── Upload Area
│   │           │   ├── Progress Indicators
│   │           │   └── Datasets Table
│   │           │
│   │           └── NotFound
```

## Data Flow: Query Submission

```
┌──────────────────────────────────────────────────────────────┐
│ User Types Natural Language Query in QueryConsole             │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
            ┌─────────────────────────┐
            │ Validate Input          │
            │ - Query not empty       │
            │ - Dataset selected      │
            └─────────────┬───────────┘
                          │
                          ▼
            ┌─────────────────────────────────────────┐
            │ Dispatch submitJob (Redux Thunk)        │
            │                                         │
            │ POST /api/v1/jobs                       │
            │ {                                       │
            │   query: "...",                         │
            │   dataset_id: "...",                    │
            │   options: {}                           │
            │ }                                       │
            └─────────────┬───────────────────────────┘
                          │
                          ▼
            ┌─────────────────────────────────────┐
            │ Backend Returns Job ID              │
            │ {                                   │
            │   job_id: "job_20251030_120000",    │
            │   status: "queued",                 │
            │   ...                               │
            │ }                                   │
            └─────────────┬───────────────────────┘
                          │
                          ▼
            ┌─────────────────────────────────────┐
            │ Store job in Redux State            │
            │ Set as currentJob                   │
            │ Display in Results Panel            │
            └─────────────┬───────────────────────┘
                          │
                          ▼
            ┌──────────────────────────────────────────┐
            │ Start Polling (Redux Thunk)              │
            │ pollJobCompletion(job_id)                │
            │                                          │
            │ Every 1 second:                          │
            │ GET /api/v1/jobs/{job_id}               │
            └─────────────┬──────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   Queued/Running    Running (>50%)    Completed
        │                 │                 │
   Update Progress   Update Progress   Get Results
   Display in UI     Display in UI     Display Insights
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                          ▼
            ┌──────────────────────────────────┐
            │ Job Completed Successfully       │
            │                                  │
            │ - Display Results/Visualizations │
            │ - Show AI Insights               │
            │ - Allow Save/Export              │
            │ - Add to Query History           │
            └──────────────────────────────────┘
```

## Redux State Structure

```javascript
{
  projects: {
    projects: [
      {
        id: "ecommerce_analysis",
        name: "E-commerce Customer Analysis",
        description: "...",
        created_at: "...",
        status: "active",
        data_sources: ["BigQuery", "Google Analytics"],
        last_updated: "..."
      },
      // ... more projects
    ],
    currentProject: null,
    loading: false,
    error: null
  },
  
  datasets: {
    datasets: [
      {
        id: "dataset_001",
        name: "customer_data.csv",
        type: "csv",
        size_bytes: 5242880,
        row_count: 50000,
        columns: [
          { name: "customer_id", type: "string", nullable: false },
          { name: "revenue", type: "number", nullable: false },
          // ... more columns
        ],
        created_at: "...",
        updated_at: "..."
      },
      // ... more datasets
    ],
    currentDataset: null,
    loading: false,
    error: null,
    uploadProgress: {
      "file.csv": 45,  // percentage
      // ... more uploads
    }
  },
  
  jobs: {
    jobs: {
      "job_20251030_120000": {
        job_id: "job_20251030_120000",
        status: "completed",
        progress: 100,
        created_at: "...",
        results: {
          summary: {
            total_records_analyzed: 1250000,
            analysis_duration_seconds: 45,
            confidence_score: 0.94
          },
          insights: [
            "Revenue increased by 23%...",
            // ... more insights
          ],
          visualizations: [
            {
              type: "line_chart",
              title: "Revenue Trend",
              data: { ... }
            },
            // ... more visualizations
          ]
        }
      }
    },
    currentJobId: "job_20251030_120000",
    loading: false,
    error: null,
    polling: false
  }
}
```

## API Request/Response Flow

### Query Submission

**Request:**
```javascript
POST /api/v1/jobs
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "Show me revenue by product category",
  "dataset_id": "dataset_001",
  "options": {
    "time_range": "last_quarter",
    "limit": 1000
  }
}
```

**Response:**
```javascript
{
  "job_id": "job_20251030_120000",
  "status": "queued",
  "message": "Analysis job created successfully",
  "estimated_completion": "2-3 minutes",
  "priority": "normal",
  "created_at": "2025-10-30T12:00:00Z",
  "queue_position": 1
}
```

### Job Status Poll

**Request:**
```javascript
GET /api/v1/jobs/job_20251030_120000
Authorization: Bearer <token>
```

**Response (Running):**
```javascript
{
  "job_id": "job_20251030_120000",
  "status": "running",
  "progress": 65,
  "created_at": "2025-10-30T12:00:00Z"
}
```

**Response (Completed):**
```javascript
{
  "job_id": "job_20251030_120000",
  "status": "completed",
  "progress": 100,
  "results": {
    "summary": { ... },
    "insights": [ ... ],
    "visualizations": [ ... ]
  },
  "created_at": "2025-10-30T12:00:00Z"
}
```

## File Upload Flow

```
User Selects File
       │
       ▼
HTML5 Drag & Drop Detected
       │
       ▼
formData = new FormData()
formData.append('file', file)
       │
       ▼
POST /api/v1/projects/{id}/datasets
       │
       ▼
onUploadProgress Callback
update uploadProgress in Redux
       │
       ▼
Server Processes Upload
       │
       ▼
Response: Dataset Metadata
{
  id: "dataset_123",
  name: "customer_data.csv",
  type: "csv",
  row_count: 50000,
  columns: [...]
}
       │
       ▼
Add to datasets list
Clear uploadProgress
Display in table
```

## Deployment Architecture

### Development
```
Localhost:3000 (Vite Dev Server)
    ├── Hot Module Replacement (HMR)
    ├── TypeScript Compilation
    └── Network Proxy to Backend
```

### Production (GCS + CDN)
```
┌─────────────────────────┐
│   User Browser          │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Cloud CDN                         │
│   - Caches dist/ files              │
│   - Global distribution             │
│   - Compression enabled             │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   Google Cloud Storage              │
│   - Serves dist/ folder             │
│   - CORS configured                 │
│   - Static website hosting          │
└─────────────────────────────────────┘
```

### Alternative Deployment (Vercel/Netlify)

```
Git Push to main
        │
        ▼
Webhook Triggered
        │
        ▼
npm run build
        │
        ▼
npm run test
        │
        ▼
Deploy to CDN
        │
        ▼
Live at https://your-app.vercel.app
```

## Performance Metrics

```
Metric                  Target
─────────────────────────────────────
Lighthouse Score        > 90
First Contentful Paint  < 1.5s
Largest Contentful Paint < 2.5s
Cumulative Layout Shift < 0.1
Time to Interactive     < 3.0s
Total Bundle Size       < 500KB (gzipped)
API Response Time       < 2s (p95)
```

## Error Handling Flow

```
API Request
     │
     ▼
Request Interceptor
- Add Auth token
     │
     ▼
Response
     │
     ├─ 2xx Success
     │  └─ Resolve Promise
     │
     └─ 4xx/5xx Error
        └─ Response Interceptor
           ├─ 401 Unauthorized
           │  └─ Redirect to Login
           │
           ├─ 403 Forbidden
           │  └─ Show Permission Error
           │
           ├─ 404 Not Found
           │  └─ Show Not Found Page
           │
           ├─ 500+ Server Error
           │  └─ Show Server Error Toast
           │
           └─ Network Error
              └─ Show Connection Error
              
    Error displayed to user via:
    - Toast notification
    - Alert box
    - Redux error state
```

## Session & Authentication

```
User Visits App
       │
       ▼
Check localStorage for token
       │
       ├─ Token exists
       │  └─ Add to API headers
       │
       └─ No token
          └─ Redirect to login
          
On API 401 Response
       │
       ▼
Clear token from localStorage
       │
       ▼
Redirect to login page
       │
       ▼
User logs in (OAuth)
       │
       ▼
Backend returns token
       │
       ▼
Store in localStorage
       │
       ▼
Redirect to dashboard
```

## Browser Storage Usage

```
localStorage
├── auth_token (JWT)
└── user_preferences
    ├── theme (light/dark)
    └── sidebar_collapsed

sessionStorage
├── temp_form_data
└── sort_preferences

IndexedDB (optional)
└── query_history (offline cache)
```

---

**This architecture ensures**:
- ✅ Scalable component structure
- ✅ Efficient state management
- ✅ Robust error handling
- ✅ Responsive user experience
- ✅ Enterprise-grade security
- ✅ High performance
