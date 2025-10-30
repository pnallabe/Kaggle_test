# 🚀 QUICK START GUIDE - CONTINUING DEVELOPMENT

## Current System Status

### ✅ Running Services
```bash
# Frontend (Port 3001)
http://localhost:3001

# Backend API (Port 8080)  
http://localhost:8080
```

### ✅ What's Working
- Dashboard displaying 4 projects
- Create project modal functional
- Projects persisted to `projects_storage.json`
- All components connected to backend
- Redux state management active
- API client ready for all endpoints

---

## Starting Development

### 1. **Start Backend** (if not running)
```bash
cd /Users/swarnabale/Documents/Pradeep_Projects/Kaggle_test
python3 main.py
```
✅ Runs on: http://localhost:8080

### 2. **Start Frontend** (if not running)
```bash
cd /Users/swarnabale/Documents/Pradeep_Projects/Kaggle_test/frontend
npm run dev
```
✅ Runs on: http://localhost:3001

### 3. **Open Browser**
```
http://localhost:3001
```

---

## Feature Implementation Guide

### Feature: Edit Project Details

**Files to Modify**:
1. `backend/main.py` - Add PUT endpoint
2. `frontend/src/store/slices/projectSlice.ts` - Add updateProject thunk
3. `frontend/src/components/pages/Dashboard.tsx` - Add edit button/modal
4. `frontend/src/components/ui/Modal.tsx` - Already has edit mode ready

**Backend Code**:
```python
@app.route('/api/v1/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    global projects_db
    data = request.get_json() or {}
    
    # Find and update project
    for project in projects_db:
        if project['id'] == project_id:
            project.update(data)
            project['last_updated'] = datetime.now().isoformat()
            save_projects()
            return jsonify({"project": project}), 200
    
    return jsonify({"error": "Project not found"}), 404
```

**Frontend Code**:
```typescript
// In projectSlice.ts
export const updateProject = createAsyncThunk(
  'projects/updateProject',
  async ({ projectId, data }: { projectId: string; data: Partial<Project> }, { rejectWithValue }) => {
    try {
      const response = await apiClient.updateProject(projectId, data);
      return (response as any).project;
    } catch (error) {
      return rejectWithValue(error);
    }
  }
);

// In API client
async updateProject(projectId: string, data: Partial<Project>) {
  return this.client.put(`/api/v1/projects/${projectId}`, data);
}
```

### Feature: Delete Project

**Backend**:
```python
@app.route('/api/v1/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    global projects_db
    projects_db = [p for p in projects_db if p['id'] != project_id]
    save_projects()
    return jsonify({"message": "Project deleted"}), 200
```

**Frontend**:
```typescript
export const deleteProject = createAsyncThunk(
  'projects/deleteProject',
  async (projectId: string, { rejectWithValue }) => {
    try {
      await apiClient.deleteProject(projectId);
      return projectId;
    } catch (error) {
      return rejectWithValue(error);
    }
  }
);
```

### Feature: Upload Dataset

**Already Connected**:
- `DatasetManager.tsx` component exists
- `uploadDataset` thunk in Redux
- Drag-and-drop UI ready
- Progress tracking ready

**Need to Add in Backend**:
```python
@app.route('/api/v1/projects/<project_id>/datasets', methods=['POST'])
def upload_dataset(project_id):
    # Handle file upload
    # Store dataset info
    # Return dataset object
    pass
```

### Feature: Query Execution

**Already Connected**:
- `QueryConsole.tsx` component  
- `submitJob` thunk in Redux
- `pollJobCompletion` thunk ready
- Results display ready

**Backend Already Has**:
- `/api/v1/jobs` POST endpoint
- `/api/v1/jobs/<job_id>` GET endpoint
- Job status tracking

---

## File Structure

```
/Users/swarnabale/Documents/Pradeep_Projects/Kaggle_test/
├── main.py                          # Flask backend
├── projects_storage.json            # Persisted data
├── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # Router config
│   │   ├── main.tsx                 # Entry point
│   │   ├── components/
│   │   │   ├── layout/              # Navbar, Sidebar, Layout
│   │   │   ├── pages/               # Dashboard, QueryConsole, DatasetManager
│   │   │   └── ui/                  # 11 reusable components
│   │   ├── store/
│   │   │   ├── store.ts             # Redux setup
│   │   │   └── slices/              # projectSlice, datasetSlice, jobSlice
│   │   ├── services/
│   │   │   └── api.ts               # Axios client (baseURL: localhost:8080)
│   │   ├── hooks/                   # useAppDispatch, useAppSelector, useToast
│   │   ├── types/                   # TypeScript interfaces
│   │   └── styles/
│   │       └── globals.css          # Tailwind + dark mode
│   ├── .env.local                   # VITE_API_URL=http://localhost:8080
│   ├── vite.config.ts               # Vite + proxy config
│   ├── tailwind.config.js
│   ├── package.json                 # npm scripts
│   └── index.html
└── docs/
    ├── FRONTEND_BACKEND_INTEGRATION_COMPLETE.md
    ├── CREATE_PROJECT_FEATURE_COMPLETE.md
    └── other docs...
```

---

## Common Tasks

### Add New API Endpoint

1. **Backend** (`main.py`):
```python
@app.route('/api/v1/your-endpoint', methods=['GET|POST|PUT|DELETE'])
def your_handler():
    # Your logic here
    return jsonify({...}), 200
```

2. **API Client** (`src/services/api.ts`):
```typescript
async yourMethod(): Promise<YourType> {
  const response = await this.client.get('/api/v1/your-endpoint');
  return response.data;
}
```

3. **Redux Slice** (`src/store/slices/yourSlice.ts`):
```typescript
export const yourThunk = createAsyncThunk(
  'your/action',
  async (params, { rejectWithValue }) => {
    try {
      return await apiClient.yourMethod();
    } catch (error) {
      return rejectWithValue(error);
    }
  }
);
```

4. **Component** (`src/components/pages/YourPage.tsx`):
```typescript
const dispatch = useAppDispatch();
const result = useAppSelector((state) => state.your);

useEffect(() => {
  dispatch(yourThunk() as any);
}, [dispatch]);
```

### Debug API Calls

**Terminal**:
```bash
# Test backend endpoints
curl http://localhost:8080/api/v1/projects
curl -X POST http://localhost:8080/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","description":"Test"}'
```

**Browser Console**:
```javascript
// Check Redux state
localStorage.getItem('persist:root')

// Check network requests
// DevTools → Network tab
```

### Rebuild Frontend

```bash
cd frontend
npm run build
# Output: dist/ folder ready for deployment
```

---

## Testing Workflow

### 1. Test Create Project
- Click "+ New Project"
- Fill form
- Click Create
- Verify project appears in list

### 2. Test Persistence
- Create a project
- Refresh page (F5)
- Verify project still there

### 3. Test API Directly
```bash
# Get all projects
curl http://localhost:8080/api/v1/projects | python3 -m json.tool

# Create project
curl -X POST http://localhost:8080/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"API Test","description":"Direct API test"}'
```

### 4. Check Redux State
- Open DevTools (F12)
- Redux DevTools extension
- View dispatched actions
- View state changes

---

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| Frontend Dev | 3001 | http://localhost:3001 |
| Backend API | 8080 | http://localhost:8080 |
| Vite HMR | 5173 | auto |

---

## Environment Variables

### Frontend (`.env.local`)
```bash
VITE_API_URL=http://localhost:8080
VITE_APP_NAME=AI Data Analyst
```

### Backend (environment)
```bash
PORT=8080              # Default: 8080
GOOGLE_CLOUD_PROJECT=  # Optional
```

---

## Git Commit Guide

```bash
# After implementing a feature
git add .
git commit -m "feat: add edit project functionality"

# Branch: feature/phase-6-mvp-release
git push origin feature/phase-6-mvp-release
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find process
lsof -i :3001
lsof -i :8080

# Kill process
kill -9 <PID>
```

### Module Not Found Errors
```bash
cd frontend
npm install
npm run dev
```

### API Connection Failed
1. Check backend running: `curl http://localhost:8080/health`
2. Check .env.local has correct URL
3. Check network tab in DevTools
4. Check backend logs

### Projects Not Persisting
1. Check `projects_storage.json` exists
2. Check write permissions: `ls -la projects_storage.json`
3. Check backend logs for save_projects() calls
4. Restart backend

---

## Next Priority Features

1. **Edit Project** - Most requested
2. **Delete Project** - Quick win
3. **Upload Dataset** - Powers queries
4. **Query Execution** - Core feature
5. **Results Display** - Show insights

---

## Performance Notes

- Redux DevTools for state inspection
- Vite HMR for instant updates
- API polling for job status (configurable)
- Skeleton loaders during data fetch

---

## Documentation Files

- `FRONTEND_BACKEND_INTEGRATION_COMPLETE.md` - Full integration details
- `CREATE_PROJECT_FEATURE_COMPLETE.md` - Feature implementation
- `FRONTEND_DEVELOPMENT_COMPLETE.md` - Dev guide
- `FRONTEND_ARCHITECTURE.md` - System architecture

---

**Happy Coding! 🚀**

Last Updated: October 30, 2025
Status: Ready for Development
