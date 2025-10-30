#!/bin/bash

# Start development environment - both backend and frontend

echo "🚀 Starting AI Data Analyst Development Environment..."
echo ""

# Kill any existing processes on ports 8080 and 3001
echo "🧹 Cleaning up ports..."
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

sleep 1

# Start backend
echo "🔧 Starting backend on port 8080..."
cd /Users/swarnabale/Documents/Pradeep_Projects/Kaggle_test
source .venv/bin/activate
python main.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
echo ""

# Wait for backend to start
sleep 3

# Start frontend
echo "⚛️  Starting frontend on port 3001..."
cd /Users/swarnabale/Documents/Pradeep_Projects/Kaggle_test/frontend
npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"
echo ""

# Show URLs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Development Environment Ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Frontend:  http://localhost:3001"
echo "🔌 Backend:   http://localhost:8080"
echo "📚 API Docs:  http://localhost:8080/docs"
echo ""
echo "📝 Demo Credentials:"
echo "   Email:    demo@example.com"
echo "   Password: demo123"
echo ""
echo "📋 Logs:"
echo "   Backend:  backend.log"
echo "   Frontend: frontend.log"
echo ""
echo "To stop: Press Ctrl+C (or kill $BACKEND_PID and $FRONTEND_PID)"
echo ""

# Keep script running and show logs
wait
