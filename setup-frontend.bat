@echo off
REM Frontend Setup Script for Windows
REM This script automates the initial setup of the AI Data Analyst frontend

echo.
echo 🚀 AI Data Analyst Frontend Setup
echo ==================================
echo.

REM Check Node.js
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Node.js is not installed. Please install Node.js 16+ first.
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i

echo ✅ Node.js version: %NODE_VERSION%
echo ✅ npm version: %NPM_VERSION%
echo.

echo 📦 Installing dependencies...
cd frontend
call npm install

echo.
echo 📝 Setting up environment file...
if not exist .env.local (
    copy .env.example .env.local
    echo ✅ Created .env.local
    echo.
    echo ⚠️  Edit .env.local and set VITE_API_URL to your backend URL
) else (
    echo ✅ .env.local already exists
)

echo.
echo ✅ Frontend setup complete!
echo.
echo 📚 Next steps:
echo 1. Edit frontend\.env.local with your backend API URL
echo 2. Run 'npm run dev' to start development server
echo 3. Open http://localhost:3000 in your browser
echo.
echo Available commands:
echo   npm run dev       - Start development server
echo   npm run build     - Build for production
echo   npm run preview   - Preview production build
echo   npm run lint      - Run linter
echo   npm run test      - Run tests
echo.
pause
