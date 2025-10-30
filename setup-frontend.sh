#!/bin/bash

# Frontend Setup Script
# This script automates the initial setup of the AI Data Analyst frontend

set -e

echo "🚀 AI Data Analyst Frontend Setup"
echo "=================================="
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"
echo ""

# Navigate to frontend directory
cd "$(dirname "$0")/frontend" || exit 1

echo "📦 Installing dependencies..."
npm install

echo ""
echo "📝 Setting up environment file..."
if [ ! -f .env.local ]; then
    cp .env.example .env.local
    echo "✅ Created .env.local"
    echo ""
    echo "⚠️  Edit .env.local and set VITE_API_URL to your backend URL"
else
    echo "✅ .env.local already exists"
fi

echo ""
echo "✅ Frontend setup complete!"
echo ""
echo "📚 Next steps:"
echo "1. Edit frontend/.env.local with your backend API URL"
echo "2. Run 'npm run dev' to start development server"
echo "3. Open http://localhost:3000 in your browser"
echo ""
echo "Available commands:"
echo "  npm run dev       - Start development server"
echo "  npm run build     - Build for production"
echo "  npm run preview   - Preview production build"
echo "  npm run lint      - Run linter"
echo "  npm run test      - Run tests"
echo ""
