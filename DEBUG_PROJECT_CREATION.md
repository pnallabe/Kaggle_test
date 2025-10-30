# Project Creation Debugging Guide

**Issue**: Login works, but project creation fails  
**Status**: Investigating  
**Date**: October 30, 2025

---

## What We Know

✅ **Login works**
- Demo account logs in successfully
- JWT token is generated and stored
- Token is visible in localStorage

❌ **Project creation fails**
- Clicking "Create Project" button doesn't seem to do anything
- Or shows an error

---

## Debugging Steps

### Step 1: Check Browser Console
1. Open browser DevTools (right-click → Inspect)
2. Go to **Console** tab
3. Try creating a project again
4. Look for any red error messages
5. **Screenshot/note the error**

### Step 2: Check Network Tab
1. Open browser DevTools
2. Go to **Network** tab
3. Try creating a project
4. Look for `/api/v1/projects` POST request
5. **Check response status and body**
   - Should be `201` (Created)
   - Body should contain project details

### Step 3: Use API Test Page
1. After login, go to: `http://localhost:3001/api-test`
2. Click "Test Create Project"
3. Check the result output
4. **Note if it succeeds or fails**

### Step 4: Check Backend Logs
```bash
tail -50 backend.log
```
Look for any error messages around the time you tried creating the project.

---

## What Changed (Recent Fixes)

✅ Fixed projectSlice to handle response correctly  
✅ Added better error handling and logging  
✅ Created APITest component for debugging  
✅ Updated API client to be more flexible with responses  

---

## Possible Issues & Solutions

### Issue: CORS Error
**Symptom**: Browser console shows "CORS policy blocked"  
**Solution**: Backend CORS already enabled with Flask-CORS  
**Check**: Verify request headers include `Authorization: Bearer <token>`

### Issue: 401 Unauthorized
**Symptom**: Network tab shows 401 response  
**Solution**: Token might be expired or not sent  
**Fix**: Login again, token should be fresh

### Issue: 500 Server Error
**Symptom**: Backend returns 500  
**Solution**: Check backend logs for error details  
**Fix**: Restart backend if needed

### Issue: Response Parsing Error
**Symptom**: "Failed to create project" but API returns 201  
**Solution**: Response format mismatch  
**Fix**: Already fixed in latest code

---

## Manual API Test Command

```bash
# 1. Get token
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "demo123"}' \
  | grep -o '"token":"[^"]*' | cut -d'"' -f4)

echo "Token: $TOKEN"

# 2. Create project with token
curl -X POST http://localhost:8080/api/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Manual Test", "description": "Testing"}'
```

---

## Frontend Logs

The frontend now logs errors to the browser console. Look for:
- `Create project error:`
- `Fetch projects error:`
- Any error messages in the Console tab

---

## What to Do Next

### Option A: Use API Test Page
1. Go to `http://localhost:3001/api-test`
2. Click "Test Create Project"
3. This directly tests the endpoint with your token
4. If this works, it's a Redux/state management issue
5. If this fails, it's an API communication issue

### Option B: Check Browser Console
1. Open DevTools Console
2. Try creating a project in the UI
3. Look for error messages
4. Share the error with debugging info

### Option C: Manual API Test
1. Run the manual test command above
2. Check if the backend creates the project successfully
3. If yes, the issue is in the frontend
4. If no, the issue is in the backend

---

## API Endpoint Details

**Endpoint**: `POST /api/v1/projects`  
**Headers**: `Authorization: Bearer <token>`  
**Body**:
```json
{
  "name": "Project Name",
  "description": "Description",
  "data_sources": []
}
```

**Success Response (201)**:
```json
{
  "project": {
    "id": "proj_20251030_121207",
    "user_id": "demo_user_20251030",
    "name": "Project Name",
    "description": "Description",
    "created_at": "2025-10-30T12:12:07.390341",
    "status": "active",
    "data_sources": [],
    "last_updated": "2025-10-30T12:12:07.390347"
  },
  "message": "Project created successfully",
  "timestamp": "2025-10-30T12:12:07.390978"
}
```

---

## Recent Backend Test Results

```
✅ Login endpoint working
✅ Token generated successfully
✅ Project creation API working
✅ Response format correct
✅ CORS headers present
```

---

## Current Status

- **Backend**: ✅ Working correctly
- **API**: ✅ Returning correct responses
- **Frontend**: 🔄 Investigating project creation flow
- **Token**: ✅ Being generated and stored
- **CORS**: ✅ Enabled and working

---

## Next Steps

1. **Check the API Test page** - This will tell us if the frontend can communicate with the API
2. **Review browser console** - This will show any JavaScript errors
3. **Check network tab** - This will show the HTTP requests/responses
4. **Review backend logs** - This will show any server-side errors

**Please try the API Test page first** and share what you see!

---

**How to Access the API Test Page**:
1. Make sure you're logged in
2. Go to: `http://localhost:3001/api-test`
3. Click the "Test Create Project" button
4. Check the result
5. Share the output so I can help fix the issue

If the test page shows the project was created successfully but the dashboard doesn't update, then it's a state management issue (Redux). If the test page fails, it's an API communication issue.
