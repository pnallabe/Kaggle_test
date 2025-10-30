# AI Data Analyst - Frontend

Modern React + TypeScript frontend for the AI Data Analyst platform.

## Features

- **Dashboard**: Overview of projects, datasets, and recent activity
- **Query Console**: Natural language query interface with real-time results
- **Dataset Manager**: Upload and manage data sources
- **Real-time Updates**: Polling-based job status tracking
- **Responsive Design**: Mobile, tablet, and desktop support
- **Dark Mode**: Built-in light and dark theme support

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool
- **Tailwind CSS** - Styling
- **Redux Toolkit** - State management
- **Axios** - HTTP client
- **React Router** - Routing
- **Plotly.js** - Data visualization

## Getting Started

### Prerequisites

- Node.js 16+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Create environment file
cp .env.example .env.local
```

### Development

```bash
# Start development server
npm run dev

# Server runs on http://localhost:3000
```

### Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Linting

```bash
# Check for linting errors
npm run lint

# Run tests
npm run test

# Run tests with UI
npm run test:ui
```

## Project Structure

```
src/
├── components/        # React components
│   ├── layout/       # Layout components (Navbar, Sidebar)
│   ├── pages/        # Page components (Dashboard, QueryConsole, etc)
│   └── ui/           # Reusable UI components (Button, Card, etc)
├── services/         # API service
├── store/            # Redux store and slices
├── hooks/            # Custom React hooks
├── types/            # TypeScript type definitions
├── utils/            # Utility functions
├── styles/           # Global styles
└── main.tsx          # App entry point
```

## Key Components

### Pages

- **Dashboard**: Projects overview and statistics
- **QueryConsole**: Query submission and results viewing
- **DatasetManager**: Dataset upload and management

### UI Components

- **Button**: Customizable button with variants
- **Card**: Reusable card container
- **Input/Textarea**: Form inputs with validation
- **DataTable**: Sortable, filterable tables
- **Loader**: Loading spinner
- **Alert**: Alert/notification component
- **Toast**: Toast notifications

## API Integration

The frontend connects to the backend API at:
- Development: `http://localhost:5000`
- Production: Set via `VITE_API_URL` environment variable

Key endpoints:
- `GET /api/v1/projects` - List projects
- `POST /api/v1/jobs` - Submit query job
- `GET /api/v1/jobs/:id` - Get job status
- `GET/POST /api/v1/datasets` - Manage datasets

## State Management

Uses Redux Toolkit with slices:
- **Projects**: Project list and current project
- **Datasets**: Dataset management
- **Jobs**: Query job tracking and results

## Styling

- **Tailwind CSS**: Utility-first CSS framework
- **Dark Mode**: CSS custom properties for theming
- **Responsive**: Mobile-first design approach

## Environment Variables

```
VITE_API_URL=http://localhost:5000
VITE_APP_NAME=AI Data Analyst
```

## Contributing

1. Follow the existing code structure
2. Use TypeScript for type safety
3. Keep components focused and reusable
4. Test before committing

## License

Proprietary - AI Data Analyst Platform
