# Frontend Quick Start Guide

## 5-Minute Setup

### Prerequisites
- Node.js 16+ installed
- Backend API running (or will run later)

### Step 1: Install Dependencies
```bash
cd frontend
npm install
```

### Step 2: Configure Environment
```bash
# Copy environment template
cp .env.example .env.local

# Edit .env.local and set your backend URL
# VITE_API_URL=http://localhost:5000
```

### Step 3: Start Development Server
```bash
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## What You Get

### ✅ Dashboard Page (`/`)
- View all projects
- Quick statistics
- Project cards with data sources

### ✅ Query Console (`/query`)
- Natural language query input
- Real-time job status tracking
- Results and insights display

### ✅ Dataset Manager (`/datasets`)
- Drag-and-drop file upload
- Sortable dataset table
- Upload progress tracking

### ✅ Layout
- Responsive sidebar navigation
- Top navbar with theme toggle
- Dark mode support

---

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx                 # Main app routing
│   ├── main.tsx                # React entry point
│   ├── components/
│   │   ├── layout/             # Layout components
│   │   ├── pages/              # Page components
│   │   └── ui/                 # Reusable UI components
│   ├── services/
│   │   └── api.ts              # API client
│   ├── store/                  # Redux state
│   ├── hooks/                  # Custom hooks
│   ├── types/                  # TypeScript types
│   ├── utils/                  # Utility functions
│   └── styles/                 # Global styles
├── vite.config.ts
├── tailwind.config.js
├── package.json
├── .env.local                  # Your configuration
└── README.md
```

---

## Key Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| React | UI Framework | 18.2.0 |
| TypeScript | Type Safety | 5.3.0 |
| Vite | Build Tool | 5.0.0 |
| Tailwind CSS | Styling | 3.3.0 |
| Redux Toolkit | State Management | 1.9.7 |
| Axios | HTTP Client | 1.6.2 |
| React Router | Routing | 6.20.0 |

---

## Available Scripts

```bash
# Development
npm run dev              # Start dev server (http://localhost:3000)

# Production
npm run build            # Build for production (outputs to dist/)
npm run preview          # Preview production build locally

# Quality
npm run lint             # Check for code style issues
npm run test             # Run tests
npm run test:coverage    # Coverage report
```

---

## API Integration

The frontend expects these endpoints from your backend:

### Projects
```
GET  /api/v1/projects              # List all projects
POST /api/v1/projects              # Create a project
GET  /api/v1/projects/:id          # Get project details
```

### Datasets
```
GET  /api/v1/projects/:id/datasets # List datasets
POST /api/v1/projects/:id/datasets # Upload dataset
```

### Jobs/Queries
```
POST /api/v1/jobs                  # Submit query job
GET  /api/v1/jobs/:id              # Get job status/results
```

### Other
```
GET  /health                       # Health check endpoint
```

---

## Configuration

### Environment Variables (.env.local)

```env
# Backend API URL
VITE_API_URL=http://localhost:5000

# App name (displayed in UI)
VITE_APP_NAME=AI Data Analyst
```

### Tailwind CSS
- Configured in `tailwind.config.js`
- Dark mode support enabled
- Custom colors and spacing

### TypeScript
- Strict mode enabled
- Path aliases configured (@components, @hooks, etc.)
- Comprehensive type definitions

---

## Common Tasks

### Adding a New Page

1. Create component in `src/components/pages/MyPage.tsx`:
```typescript
import { FC } from 'react';

const MyPage: FC = () => {
  return <div>My Page</div>;
};

export default MyPage;
```

2. Add route in `src/App.tsx`:
```typescript
<Route path="/mypage" element={<MyPage />} />
```

### Adding Redux State

1. Create slice in `src/store/slices/mySlice.ts`
2. Add to store in `src/store/store.ts`
3. Use with hooks: `useAppSelector((state) => state.mySlice)`

### Using UI Components

```typescript
import { Button, Card, CardContent, Input } from '@components/ui';

<Card>
  <CardContent>
    <Input label="Name" placeholder="Enter name" />
    <Button onClick={() => alert('Clicked!')}>Submit</Button>
  </CardContent>
</Card>
```

### API Calls

```typescript
import { apiClient } from '@services/api';

// Get data
const projects = await apiClient.getProjects();

// Submit query
const job = await apiClient.submitJob({
  query: "...",
  dataset_id: "..."
});

// Poll for results
const result = await apiClient.pollJobStatus(jobId);
```

---

## Deployment

### Option 1: Google Cloud Storage + CDN
```bash
npm run build
gsutil -m cp -r dist/* gs://your-bucket/
```

### Option 2: Vercel/Netlify
- Connect your GitHub repo
- Set build command: `npm run build`
- Auto-deploys on push to main

### Option 3: Docker
```dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

---

## Troubleshooting

### Port 3000 Already in Use
```bash
npm run dev -- --port 3001
```

### Dependencies Not Installing
```bash
rm -rf node_modules package-lock.json
npm install
```

### CORS Errors
- Check backend API URL in `.env.local`
- Ensure backend has CORS configured
- Verify backend is running on correct port

### TypeScript Errors
```bash
# Clear cache and rebuild
rm -rf dist .vite
npm run build
```

### Blank Page on Load
- Open browser DevTools (F12)
- Check Console tab for errors
- Verify API URL is correct
- Check Network tab for failed requests

---

## Next Steps

1. ✅ Setup complete!
2. ⚡ Start dev server: `npm run dev`
3. 🔗 Connect your backend API
4. 🎨 Customize styling and colors
5. 📦 Deploy to production

---

## Getting Help

- **Frontend README**: `frontend/README.md`
- **Architecture Guide**: `FRONTEND_ARCHITECTURE.md`
- **System Design**: `Frontend_System_Design_doc.md`
- **API Documentation**: `docs/API_DOCUMENTATION.md`

---

## Key Features Built

✅ Dashboard with project overview  
✅ Query console with natural language input  
✅ Real-time job status tracking  
✅ Dataset upload and management  
✅ Redux state management  
✅ Responsive design (mobile/tablet/desktop)  
✅ Dark mode support  
✅ Error handling and validation  
✅ Loading states and skeletons  
✅ Reusable UI component library  

---

**Ready to start? Run `npm run dev` in the frontend directory!** 🚀
