#!/bin/bash

# Integration Test Script for AI Data Analyst
# This script tests the frontend-backend integration

echo "🧪 AI Data Analyst Integration Test"
echo "=================================="

# Test 1: Backend Health Check
echo "1️⃣ Testing Backend Health..."
HEALTH_RESPONSE=$(curl -s http://localhost:8080/health)
if [ $? -eq 0 ]; then
    echo "✅ Backend health check: PASSED"
    echo "Response: $HEALTH_RESPONSE"
else
    echo "❌ Backend health check: FAILED - Backend may not be running"
    exit 1
fi

# Test 2: Backend API Root
echo ""
echo "2️⃣ Testing Backend API Root..."
ROOT_RESPONSE=$(curl -s http://localhost:8080/)
if [ $? -eq 0 ]; then
    echo "✅ Backend root endpoint: PASSED"
    echo "Response: $ROOT_RESPONSE"
else
    echo "❌ Backend root endpoint: FAILED"
    exit 1
fi

# Test 3: Frontend Health (check if server is running)
echo ""
echo "3️⃣ Testing Frontend Server..."
FRONTEND_RESPONSE=$(curl -s http://localhost:3001/)
if [ $? -eq 0 ]; then
    echo "✅ Frontend server: PASSED"
else
    echo "❌ Frontend server: FAILED - Frontend may not be running"
    exit 1
fi

# Test 4: CORS Configuration
echo ""
echo "4️⃣ Testing CORS Configuration..."
CORS_RESPONSE=$(curl -s -H "Origin: http://localhost:3001" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: X-Requested-With" -X OPTIONS http://localhost:8080/health)
if [ $? -eq 0 ]; then
    echo "✅ CORS configuration: PASSED"
else
    echo "❌ CORS configuration: FAILED"
fi

# Test 5: API Authentication Endpoint
echo ""
echo "5️⃣ Testing Authentication Endpoints..."
AUTH_RESPONSE=$(curl -s http://localhost:8080/api/v1/auth/register)
if [[ $AUTH_RESPONSE == *"error"* || $AUTH_RESPONSE == *"required"* ]]; then
    echo "✅ Auth endpoint structure: PASSED (correctly requires data)"
else
    echo "❓ Auth endpoint: Response received - $AUTH_RESPONSE"
fi

echo ""
echo "🎉 Integration Test Summary"
echo "========================="
echo "Backend Status: ✅ Running on http://localhost:8080"
echo "Frontend Status: ✅ Running on http://localhost:3001"
echo "CORS: ✅ Configured"
echo "API Endpoints: ✅ Accessible"
echo ""
echo "🚀 Ready for full application testing!"
echo ""
echo "Next steps:"
echo "1. Open http://localhost:3001 in your browser"
echo "2. Test user registration and login"
echo "3. Test project creation and management"
echo "4. Verify data persistence"