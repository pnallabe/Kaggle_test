# Authentication System - Implementation Context & Guide

## Current Directory Structure

```
/Kaggle_test/
├── main.py                          # Current MVP backend (NO auth)
├── main_auth.py                     # NEW: Full auth backend (to replace main.py)
├── requirements.txt                 # Updated with JWT, bcrypt, python-dotenv
├── projects_storage.json            # Current projects (flat - no user scoping)
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Current routing (needs auth routes)
│   │   ├── main.tsx                # Redux Provider
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Layout.tsx      # Main layout
│   │   │   │   ├── Navbar.tsx      # Top nav
│   │   │   │   └── Sidebar.tsx     # Left nav
│   │   │   │
│   │   │   ├── pages/
│   │   │   │   ├── Dashboard.tsx       # User projects
│   │   │   │   ├── QueryConsole.tsx    # Query interface
│   │   │   │   ├── DatasetManager.tsx  # Datasets
│   │   │   │   └── NotFound.tsx        # 404 page
│   │   │   │   ├── Login.tsx           # NEW: Login page
│   │   │   │   ├── Register.tsx        # NEW: Register page
│   │   │   │   └── UserProfile.tsx     # NEW: User account
│   │   │   │
│   │   │   └── ui/ (11 reusable components)
│   │   │
│   │   ├── store/
│   │   │   ├── store.ts            # Redux store config
│   │   │   └── slices/
│   │   │       ├── projectSlice.ts
│   │   │       ├── datasetSlice.ts
│   │   │       ├── jobSlice.ts
│   │   │       └── authSlice.ts    # NEW: Auth state management
│   │   │
│   │   ├── services/
│   │   │   └── api.ts              # Axios client (needs auth methods)
│   │   │
│   │   ├── types/
│   │   │   └── index.ts            # Types (add auth types)
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAppDispatch.ts
│   │   │   ├── useAppSelector.ts
│   │   │   └── useToast.ts
│   │   │
│   │   ├── utils/
│   │   │   └── cn.ts
│   │   │
│   │   └── styles/
│   │       └── globals.css
│   │
│   └── .env.local                  # Config (VITE_API_URL, etc)
│
└── data/ (NEW - storage location)
    ├── users.json                  # User accounts (NEW)
    ├── projects.json               # User-scoped projects (NEW)
    └── datasets.json               # User-scoped datasets (NEW)
```

---

## Backend Architecture (main_auth.py)

### Key Features
✓ **JWT Authentication** - Token-based auth with 24-hour expiration
✓ **Password Hashing** - bcrypt hashing for security
✓ **User-Scoped Data** - Projects and datasets per user
✓ **Storage Limits** - 100MB per user by default
✓ **User Profiles** - Name, email, avatar, bio, organization, settings

### Storage Structure

**users.json**
```json
{
  "user@email.com": {
    "user_id": "user_20251030123456_7890",
    "email": "user@email.com",
    "name": "John Doe",
    "password_hash": "$2b$12$...",
    "created_at": "2025-10-30T...",
    "profile": {
      "avatar_url": null,
      "bio": "",
      "organization": "",
      "phone": ""
    },
    "settings": {
      "dark_mode": true,
      "notifications_enabled": true,
      "notifications_email": true
    },
    "storage": {
      "used_mb": 15.5,
      "max_mb": 100
    }
  }
}
```

**projects.json** (keyed by user_id)
```json
{
  "user_20251030123456_7890": [
    {
      "id": "proj_20251030_120000",
      "user_id": "user_20251030123456_7890",
      "name": "Sales Analysis",
      "description": "...",
      "created_at": "2025-10-30T...",
      "status": "active",
      "last_updated": "2025-10-30T..."
    }
  ]
}
```

**datasets.json** (keyed by user_id)
```json
{
  "user_20251030123456_7890": [
    {
      "id": "dataset_20251030_120000",
      "user_id": "user_20251030123456_7890",
      "name": "Sales Data",
      "file_name": "sales_2025.csv",
      "file_type": "csv",
      "size_bytes": 15728640,
      "rows": 50000,
      "columns": 25,
      "column_names": ["id", "date", "amount", ...],
      "created_at": "2025-10-30T...",
      "project_id": "proj_20251030_120000",
      "description": "..."
    }
  ]
}
```

### API Endpoints

#### Authentication
```
POST   /api/v1/auth/register         # Register new user
POST   /api/v1/auth/login            # Login user
GET    /api/v1/auth/profile          # Get user profile (requires auth)
PUT    /api/v1/auth/profile          # Update profile (requires auth)
```

#### Projects (all require auth)
```
GET    /api/v1/projects              # List user's projects
POST   /api/v1/projects              # Create project
GET    /api/v1/projects/<id>         # Get specific project
PUT    /api/v1/projects/<id>         # Update project
DELETE /api/v1/projects/<id>         # Delete project
```

#### Datasets (all require auth)
```
GET    /api/v1/datasets              # List user's datasets
POST   /api/v1/datasets              # Upload dataset
GET    /api/v1/datasets/<id>         # Get dataset
DELETE /api/v1/datasets/<id>         # Delete dataset
```

#### Jobs (all require auth)
```
POST   /api/v1/jobs                  # Submit query job
GET    /api/v1/jobs/<id>             # Get job status
```

---

## Frontend Architecture

### Redux State Management

#### Auth Slice (authSlice.ts - NEW)
```typescript
interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
  isAuthenticated: boolean
}

Actions:
- loginUser (email, password) -> JWT token
- registerUser (email, password, name) -> JWT token + user
- logoutUser () -> clear state
- loadUserProfile () -> fetch user profile
- updateProfile (updates) -> save profile
```

#### Project Slice (projectSlice.ts - UPDATE)
```typescript
interface ProjectState {
  projects: Project[]
  currentProject: Project | null
  loading: boolean
  error: string | null
}

Updated to include:
- user_id in each project
- fetchProjects now auto-filters by current user_id
```

#### Dataset Slice (datasetSlice.ts - UPDATE)
```typescript
interface DatasetState {
  datasets: Dataset[]
  loading: boolean
  error: string | null
  storageUsed: number
  storageMax: number
}

Updated to include:
- uploadDataset with progress tracking
- check storage limits before upload
- track storage usage per user
```

### Components Needed

#### PrivateRoute.tsx
```typescript
// Wrapper component that checks authentication
// If not authenticated: redirect to /login
// If authenticated: render component
```

#### Login.tsx
```typescript
Form inputs:
- Email
- Password

Buttons:
- Login
- Link to Register

Validation:
- Email format
- Password length
- API error handling

On success:
- Save token to localStorage
- Save user to Redux
- Redirect to dashboard
```

#### Register.tsx
```typescript
Form inputs:
- Name
- Email
- Password
- Confirm Password

Validation:
- All fields required
- Email format
- Password >= 6 chars
- Passwords match
- Email not already used (409 from API)

On success:
- Save token to localStorage
- Save user to Redux
- Redirect to dashboard
```

#### UserProfile.tsx
```typescript
Display:
- User info (name, email, created_at)
- Profile settings (avatar, bio, organization, phone)
- Preferences (dark mode, notifications)
- Storage usage (X MB / 100 MB)
- Logout button

Edit mode:
- Update name, bio, organization, phone
- Toggle dark mode
- Toggle notifications
- Save button with validation
```

### API Client Updates (api.ts)

```typescript
// Add auth methods
async register(email: string, password: string, name: string)
async login(email: string, password: string)
async logout()
async getProfile()
async updateProfile(updates)

// Updated project methods (with user_id)
async getProjects()  // Now auto-scoped to user
async createProject(name, description)
async updateProject(id, updates)
async deleteProject(id)

// Dataset methods (with user_id)
async getDatasets()  // Now auto-scoped to user
async uploadDataset(file, projectId)
async deleteDataset(id)

// Token handling
- Store token in localStorage
- Add to all requests as Authorization header
- Refresh token on 401
- Auto-redirect to /login on 401 errors
```

### Types Update (types/index.ts)

Add:
```typescript
interface User {
  user_id: string
  email: string
  name: string
  created_at: string
  profile: {
    avatar_url: string | null
    bio: string
    organization: string
    phone: string
  }
  settings: {
    dark_mode: boolean
    notifications_enabled: boolean
    notifications_email: boolean
  }
  storage: {
    used_mb: number
    max_mb: number
    percentage_used: number
  }
}

interface AuthResponse {
  user: User
  token: string
  message: string
}

interface Project {
  id: string
  user_id: string  // NEW: scope to user
  name: string
  // ... rest of fields
}

interface Dataset {
  id: string
  user_id: string  // NEW: scope to user
  // ... rest of fields
}
```

---

## Implementation Steps

### Step 1: Backend Setup
- [x] Update requirements.txt with dependencies
- [x] Create main_auth.py with full auth system
- [ ] Replace main.py with main_auth.py when ready

### Step 2: Frontend Types & Setup
- [ ] Update types/index.ts with User, AuthResponse
- [ ] Update store/store.ts to include authSlice

### Step 3: Authentication Redux
- [ ] Create store/slices/authSlice.ts with login/register/logout
- [ ] Update api.ts with auth endpoints

### Step 4: Frontend Pages
- [ ] Create components/pages/Login.tsx
- [ ] Create components/pages/Register.tsx
- [ ] Create components/pages/UserProfile.tsx
- [ ] Create components/PrivateRoute.tsx

### Step 5: Routing & Integration
- [ ] Update App.tsx with auth routes
- [ ] Wrap protected routes with PrivateRoute
- [ ] Update Navbar with user menu
- [ ] Update API calls to use auth token

### Step 6: Testing
- [ ] Test registration with validation
- [ ] Test login with token storage
- [ ] Test project creation (user-scoped)
- [ ] Test dataset upload with storage limits
- [ ] Test logout and re-login
- [ ] Test token expiration
- [ ] Test data persistence

---

## Key Design Decisions

### 1. User-Scoped Data
- Each user has separate projects and datasets
- Data stored by user_id in JSON objects
- Ensures privacy and data isolation
- Frontend automatically filters by current user_id

### 2. JWT Tokens
- 24-hour expiration
- Stored in localStorage
- Sent in Authorization header (Bearer <token>)
- Auto-refresh on 401 response

### 3. Storage Limits
- 100MB per user default (configurable)
- Checked before dataset upload
- Usage tracked in user profile
- Graceful error message if limit exceeded

### 4. Password Security
- bcrypt hashing with salt
- Minimum 6 characters
- Not stored in plain text
- Verification on login

### 5. File Structure
- Data stored in /data directory (created on startup)
- Separate JSON files for users, projects, datasets
- Easy to migrate to database later
- No external database needed for MVP

---

## Current Status

**Backend**: ✅ Complete (main_auth.py)
- All endpoints implemented
- All validation in place
- Storage functions working
- JWT token generation ready

**Frontend**: ⏳ In Progress
- Next: Types and Redux auth slice
- Then: Login/Register/Profile pages
- Then: Routing with PrivateRoute
- Then: Integration testing

**Testing**: ⏳ Not Started
- Need to test end-to-end auth flow
- Verify user data isolation
- Test storage limits
- Verify token refresh

---

## How to Test Backend

### Test Registration
```bash
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "name": "John Doe"
  }'
```

### Test Login
```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### Test Protected Endpoint (with token)
```bash
# Copy token from login response
curl -X GET http://localhost:8080/api/v1/auth/profile \
  -H "Authorization: Bearer <TOKEN>"
```

### Test Create Project (with token)
```bash
curl -X POST http://localhost:8080/api/v1/projects \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Project",
    "description": "Test project"
  }'
```

---

## Notes

- Backend is **ready to use** - just need to install dependencies and replace main.py
- Frontend needs **6-8 hours** of implementation work
- Authentication is **stateless** (JWT) - no session management needed
- Storage is **file-based** - easy to migrate to database later
- System is **scalable** - can add rate limiting, email verification later

