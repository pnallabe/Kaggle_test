#!/bin/bash

# AI Data Analyst Startup Script
# Starts both backend and frontend services

echo "🚀 Starting AI Data Analyst Application"
echo "======================================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the project root directory."
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo "❌ Error: frontend directory not found. Please run this script from the project root directory."
    exit 1
fi

# Kill any existing processes on our ports
echo "🧹 Cleaning up existing processes..."
pkill -f "python3 main.py" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true

# Wait a moment for processes to stop
sleep 2

# Start backend
echo "🔧 Starting Backend Server (Flask)..."
python3 main.py &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Test backend
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ Backend started successfully on http://localhost:8080"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Start frontend
echo "🎨 Starting Frontend Server (Vite)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 5

# Test frontend
if curl -s http://localhost:3001/ > /dev/null; then
    echo "✅ Frontend started successfully on http://localhost:3001"
else
    echo "❌ Frontend failed to start"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo "🎉 AI Data Analyst Application Started Successfully!"
echo "=================================================="
echo "Backend API: http://localhost:8080"
echo "Frontend UI: http://localhost:3001" 
echo ""
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop the services:"
echo "kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Or press Ctrl+C to stop both services"

# Function to handle cleanup on script exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "Services stopped."
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Keep script running and monitor processes
echo "🔄 Monitoring services... (Press Ctrl+C to stop)"
while true; do
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "❌ Backend process died!"
        kill $FRONTEND_PID 2>/dev/null || true
        exit 1
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "❌ Frontend process died!"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    
    sleep 5
done