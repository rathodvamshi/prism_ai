# 🔧 Render Deployment - Complete Fix Guide

## 🔴 Current Issue

Render is still running the old gunicorn command:
```
==> Running 'gunicorn app.main:app -k uvicorn'
Error: class uri 'uvicorn' invalid or not found
```

**Reason**: Render cached the old build. The Procfile has been fixed, but Render needs to clear cache and rebuild.

---

## ✅ Solution: Clear Cache & Redeploy

### Step 1: Clear Render Cache (CRITICAL)

1. Go to https://render.com/dashboard
2. Select **"prism-api"** service
3. Click **"Settings"** tab
4. Scroll down to **"Clear Build Cache"**
5. Click **"Clear"** button
6. Confirm the action

### Step 2: Manual Redeploy

1. Go back to **"Deployments"** tab
2. Click **"Manual Deploy"** button
3. Wait 10-15 minutes for full rebuild
4. Monitor logs for success

---

## 📋 What Changed in Procfile

**OLD (Broken)**:
```bash
web: gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker --timeout 120
```

**NEW (Fixed)**:
```bash
web: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
```

---

## 🚀 Step-by-Step Fix Process

### Step 1: Clear Cache (2 minutes)
```
1. Render Dashboard
2. prism-api service
3. Settings tab
4. Clear Build Cache
5. Confirm
```

### Step 2: Redeploy (1 minute)
```
1. Deployments tab
2. Manual Deploy button
3. Wait for build
```

### Step 3: Monitor Build (10-15 minutes)
```
1. Watch Logs tab
2. Look for: "Uvicorn running on http://0.0.0.0:PORT"
3. Look for: "✅ MongoDB warmed up"
4. Look for: "✅ Redis warmed up"
5. No error messages
```

### Step 4: Verify (1 minute)
```bash
curl https://prism-api.onrender.com/health
# Expected: {"status": "healthy", ...}
```

---

## 🎯 Expected Build Output

After clearing cache and redeploying, you should see:

```
==> Build successful 🎉
==> Deploying...
==> Running 'python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4'
==> Uvicorn running on http://0.0.0.0:PORT
✅ MongoDB warmed up
✅ Redis warmed up
✅ Neo4j warmed up
==> Service is live
```

---

## ⏱️ Timeline

```
NOW:           Clear cache on Render
1 min:         Start manual redeploy
2-5 min:       Build starts
5-15 min:      Dependencies install
15-20 min:     Service starts
20-25 min:     Backend LIVE ✅
```

---

## 🔍 Troubleshooting

### If Still Getting Same Error

**Check 1**: Did you clear the cache?
- Go to Settings → Clear Build Cache
- Make sure you clicked "Clear"

**Check 2**: Did you redeploy after clearing?
- Go to Deployments → Manual Deploy
- Wait for new build to start

**Check 3**: Check the logs
- Render Dashboard → Logs
- Look for the new build (should say "Uvicorn running")

### If Build Still Fails

**Option 1**: Force rebuild
1. Make a small change to Procfile (add comment)
2. Push to GitHub
3. Render will auto-redeploy

**Option 2**: Delete and recreate service
1. Go to Settings → Delete Service
2. Create new Web Service
3. Reconfigure with correct settings

---

## ✅ Success Indicators

After successful deployment:

- [ ] Render shows "Live" status (green)
- [ ] Logs show "Uvicorn running on http://0.0.0.0:PORT"
- [ ] No "gunicorn" or "uvicorn.workers" errors
- [ ] Health endpoint returns 200
- [ ] Databases connected
- [ ] Ready for frontend

---

## 📊 Current Status

```
✅ Procfile Fixed (correct command)
✅ Code Pushed to GitHub
⏳ Render Cache Needs Clearing
⏳ Waiting for Manual Redeploy
⏳ Backend Coming Online
```

---

## 🎯 Action Required NOW

1. **Clear Render Cache** (Settings → Clear Build Cache)
2. **Manual Redeploy** (Deployments → Manual Deploy)
3. **Wait 15-20 minutes** for build
4. **Verify** with health endpoint

---

## 📞 If Issues Persist

### Check These:
1. **Cache cleared?** Settings → Clear Build Cache
2. **Redeployed?** Deployments → Manual Deploy
3. **Logs show Uvicorn?** Logs tab
4. **Health endpoint?** curl https://prism-api.onrender.com/health

### Get Help:
- See: `RENDER_DEPLOYMENT_FIX.md` for detailed info
- See: `DEPLOYMENT_ISSUES_SOLUTIONS.md` for common problems
- Check: Render logs for specific error messages

---

**Status**: ✅ Fix ready, waiting for cache clear + redeploy

**Next Action**: Clear cache and redeploy on Render NOW! ⚡
