# 🔧 Render Deployment Fix

## Issue
```
Error: class uri 'uvicorn' invalid or not found
ImportError: Entry point ('gunicorn.workers', 'uvicorn') not found
```

## Root Cause
The Procfile was using `gunicorn` with `uvicorn.workers.UvicornWorker` which requires additional dependencies not installed.

## Solution

### Step 1: Update Procfile
The Procfile has been updated to use direct uvicorn instead of gunicorn:

**Old (Broken)**:
```
web: gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker --timeout 120
```

**New (Fixed)**:
```
web: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
```

### Step 2: Push Changes to GitHub
```bash
git add prism-backend/Procfile DEPLOYMENT_STEP_BY_STEP.md
git commit -m "fix: Update Procfile to use uvicorn directly instead of gunicorn"
git push origin main
```

### Step 3: Redeploy on Render

**Option A: Manual Redeploy**
1. Go to Render Dashboard
2. Select "prism-api" service
3. Click "Manual Deploy"
4. Wait for deployment (5-10 minutes)
5. Check logs for success

**Option B: Auto Redeploy**
- Since you pushed to GitHub, Render should auto-redeploy
- Check Render Dashboard for deployment status

### Step 4: Verify Deployment

```bash
# Test health endpoint
curl https://prism-api.onrender.com/health

# Expected response:
# {"status": "healthy", ...}

# Check logs
# Render Dashboard → prism-api → Logs
# Look for: "Uvicorn running on http://0.0.0.0:PORT"
```

---

## Why This Works

### Uvicorn Direct
- ✅ Simpler and more reliable
- ✅ No additional worker dependencies needed
- ✅ Built-in async support
- ✅ Handles multiple workers natively
- ✅ Recommended for FastAPI on Render

### Gunicorn + Uvicorn Workers
- ❌ Requires additional dependencies
- ❌ More complex setup
- ❌ Can have compatibility issues
- ❌ Not necessary for FastAPI

---

## Alternative Commands (If Needed)

### If you want to use Gunicorn (requires uvicorn[standard])
```bash
# Make sure requirements.txt has:
# uvicorn[standard]>=0.24.0

# Then use:
web: gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 4 --timeout 120
```

### If you want more workers
```bash
# For more concurrent requests:
web: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 8
```

### If you want to limit workers
```bash
# For limited resources:
web: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
```

---

## Troubleshooting

### Still Getting Errors?

**Error: "Address already in use"**
- Solution: Render automatically assigns PORT via $PORT variable
- The command uses $PORT, so this shouldn't happen

**Error: "Module not found"**
- Solution: Verify requirements.txt is complete
- Run: `pip install -r requirements.txt` locally to test

**Error: "Connection refused"**
- Solution: Check database URLs and IP whitelist
- Verify all environment variables are set in Render

**Error: "Timeout"**
- Solution: Increase startup time
- Add to environment: `STARTUP_TIMEOUT_SECONDS=60`

---

## Verification Checklist

After redeployment:

- [ ] Render shows "Live" status
- [ ] Logs show "Uvicorn running"
- [ ] No error messages in logs
- [ ] Health endpoint returns 200
- [ ] Databases are connected
- [ ] No connection errors

---

## Next Steps

1. ✅ Push changes to GitHub
2. ✅ Redeploy on Render
3. ✅ Verify health endpoint
4. ✅ Check logs
5. ✅ Test API calls from frontend

---

## Files Updated

- ✅ `prism-backend/Procfile` - Fixed start command
- ✅ `DEPLOYMENT_STEP_BY_STEP.md` - Updated instructions
- ✅ `RENDER_DEPLOYMENT_FIX.md` - This file

---

**Status**: ✅ Fix applied and ready to redeploy

**Time to Fix**: 2-3 minutes (push + redeploy)

**Expected Result**: Successful deployment with no errors
