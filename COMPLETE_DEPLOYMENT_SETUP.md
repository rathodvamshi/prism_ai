# 🚀 Complete Deployment Setup - Vercel & Render

## 📋 Table of Contents
1. [Backend Setup (Render)](#backend-setup-render)
2. [Frontend Setup (Vercel)](#frontend-setup-vercel)
3. [Connect Services](#connect-services)
4. [Verification](#verification)

---

## Backend Setup (Render)

### Step 1: Clear Cache & Redeploy

**CRITICAL**: The old build is cached. You must clear it.

1. Go to https://render.com/dashboard
2. Select **"prism-api"** service
3. Click **"Settings"** tab
4. Scroll to **"Clear Build Cache"**
5. Click **"Clear"** button
6. Go to **"Deployments"** tab
7. Click **"Manual Deploy"**
8. Wait 15-20 minutes

### Step 2: Verify Backend is Running

```bash
# Test health endpoint
curl https://prism-api.onrender.com/health

# Expected response:
# {"status": "healthy", "timestamp": "...", ...}
# Status: 200
```

### Step 3: Check Logs

1. Render Dashboard → prism-api → Logs
2. Look for:
   - ✅ "Uvicorn running on http://0.0.0.0:PORT"
   - ✅ "✅ MongoDB warmed up"
   - ✅ "✅ Redis warmed up"
   - ✅ "✅ Neo4j warmed up"
3. Should NOT see:
   - ❌ "gunicorn" errors
   - ❌ "uvicorn.workers" errors
   - ❌ Connection errors

### Step 4: Get Backend URL

Once deployed successfully:
- Backend URL: `https://prism-api.onrender.com`
- Save this URL - you'll need it for frontend

---

## Frontend Setup (Vercel)

### Step 1: Fix Environment Variables

The issue: `vercel.json` was referencing a non-existent secret.

**Solution**: We removed the secret reference. Now you'll set the variable directly in Vercel.

### Step 2: Create/Update Vercel Project

#### Option A: If Project Already Exists

1. Go to https://vercel.com/dashboard
2. Select **"prism-ai-frontend"** project
3. Go to **"Settings"** → **"Environment Variables"**
4. Delete any existing `VITE_API_URL` variables
5. Click **"Add New"**
6. Fill in:
   ```
   Name: VITE_API_URL
   Value: https://prism-api.onrender.com
   Environments: Production, Preview, Development
   ```
7. Click **"Add"**
8. Go to **"Deployments"**
9. Click **"Redeploy"** on latest deployment
10. Wait 3-5 minutes

#### Option B: If Creating New Project

1. Go to https://vercel.com/dashboard
2. Click **"Add New"** → **"Project"**
3. Click **"Import Git Repository"**
4. Search for **"prism_ai"**
5. Click **"Import"**
6. Configure:
   ```
   Project Name: prism-ai-frontend
   Framework: Vite
   Root Directory: Frontend
   Build Command: npm run build
   Output Directory: dist
   Install Command: npm install
   ```
7. Click **"Environment Variables"**
8. Add:
   ```
   Name: VITE_API_URL
   Value: https://prism-api.onrender.com
   Environments: Production, Preview, Development
   ```
9. Click **"Deploy"**
10. Wait 3-5 minutes

### Step 3: Verify Frontend is Running

1. Visit your Vercel URL: `https://prism-ai-frontend.vercel.app`
2. Expected: Page loads without errors
3. Open DevTools: F12 → Console
4. Expected: No errors

### Step 4: Check Vercel Logs

1. Vercel Dashboard → prism-ai-frontend → Deployments
2. Click on latest deployment
3. Look for:
   - ✅ "Build completed successfully"
   - ✅ "Deployment successful"
4. Should NOT see:
   - ❌ "Build failed"
   - ❌ "VITE_API_URL" errors
   - ❌ "nodeVersion" errors

### Step 5: Get Frontend URL

Once deployed successfully:
- Frontend URL: `https://prism-ai-frontend.vercel.app`
- Save this URL - you'll need it for backend CORS

---

## Connect Services

### Step 1: Update Backend CORS

Now that you have both URLs, update backend CORS:

1. Go to https://render.com/dashboard
2. Select **"prism-api"** service
3. Go to **"Environment"** tab
4. Find **"CORS_ORIGINS"**
5. Update value:
   ```
   https://prism-ai-frontend.vercel.app
   ```
6. Click **"Save"**
7. Service will auto-redeploy (2-3 minutes)

### Step 2: Verify Connection

1. Visit frontend: `https://prism-ai-frontend.vercel.app`
2. Open DevTools: F12 → Console
3. Run this command:
   ```javascript
   fetch('https://prism-api.onrender.com/health')
     .then(r => r.json())
     .then(d => console.log('✅ Connected:', d))
     .catch(e => console.error('❌ Error:', e))
   ```
4. Expected: "✅ Connected: {status: "healthy", ...}"
5. Should NOT see: CORS errors

---

## Verification

### Backend Verification

```bash
# 1. Health check
curl https://prism-api.onrender.com/health
# Expected: 200 status, {"status": "healthy", ...}

# 2. Performance stats
curl https://prism-api.onrender.com/performance-stats
# Expected: Performance metrics

# 3. Check logs
# Render Dashboard → Logs
# Expected: No errors, all services connected
```

### Frontend Verification

```bash
# 1. Page loads
curl -I https://prism-ai-frontend.vercel.app
# Expected: 200 status

# 2. Check build
# Vercel Dashboard → Deployments
# Expected: "Ready" status

# 3. Browser console
# F12 → Console
# Expected: No errors
```

### Integration Verification

1. **API Connectivity**
   - Browser console: `fetch('https://prism-api.onrender.com/health')`
   - Expected: Response logged, no CORS errors

2. **CORS Headers**
   - DevTools → Network tab
   - Click any API request
   - Headers tab
   - Expected: `Access-Control-Allow-Origin: https://prism-ai-frontend.vercel.app`

3. **Database Connection**
   - Render logs
   - Expected: "✅ MongoDB warmed up", "✅ Redis warmed up"

4. **Full Stack**
   - Use the application
   - Expected: All features work, no errors

---

## 🎯 Complete Checklist

### Backend (Render)
- [ ] Cache cleared
- [ ] Manual redeploy started
- [ ] Build completed (15-20 min)
- [ ] Logs show "Uvicorn running"
- [ ] No gunicorn/uvicorn.workers errors
- [ ] Health endpoint returns 200
- [ ] Databases connected
- [ ] URL: https://prism-api.onrender.com

### Frontend (Vercel)
- [ ] Environment variable VITE_API_URL set
- [ ] Value: https://prism-api.onrender.com
- [ ] Environments: Production, Preview, Development
- [ ] Redeployed
- [ ] Build completed (3-5 min)
- [ ] Page loads without errors
- [ ] No console errors
- [ ] URL: https://prism-ai-frontend.vercel.app

### Connection
- [ ] CORS_ORIGINS updated in Render
- [ ] Value: https://prism-ai-frontend.vercel.app
- [ ] Backend redeployed
- [ ] API calls work from frontend
- [ ] No CORS errors
- [ ] Full integration working

---

## ⏱️ Timeline

```
Backend Setup:
  0 min:   Clear cache
  1 min:   Manual redeploy
  2-20 min: Build & deploy
  20 min:  Backend LIVE ✅

Frontend Setup:
  20 min:  Set environment variable
  21 min:  Redeploy
  21-25 min: Build & deploy
  25 min:  Frontend LIVE ✅

Connection:
  25 min:  Update CORS
  26 min:  Backend redeploy
  28 min:  Full Stack LIVE ✅
```

**Total Time**: 30 minutes

---

## 🚨 Troubleshooting

### Backend Issues

**Error: "gunicorn app.main:app -k uvicorn"**
- Solution: Clear cache and redeploy
- Render Dashboard → Settings → Clear Build Cache

**Error: "Connection refused"**
- Solution: Check database URLs and IP whitelist
- MongoDB Atlas → Network Access → Add 0.0.0.0/0

**Error: "Module not found"**
- Solution: Verify requirements.txt
- Run locally: `pip install -r requirements.txt`

### Frontend Issues

**Error: "VITE_API_URL references Secret which does not exist"**
- Solution: Remove secret reference from vercel.json (DONE)
- Set variable directly in Vercel dashboard

**Error: "Build failed"**
- Solution: Clear cache and reinstall
- Run locally: `npm cache clean --force && npm install && npm run build`

**Error: "Page won't load"**
- Solution: Check browser console (F12)
- Check Vercel build logs
- Verify VITE_API_URL is set

### Connection Issues

**Error: "CORS error"**
- Solution: Update CORS_ORIGINS in Render
- Value: https://prism-ai-frontend.vercel.app

**Error: "API calls fail"**
- Solution: Verify backend URL is correct
- Test: `curl https://prism-api.onrender.com/health`

---

## 📞 Quick Reference

| Service | URL | Status |
|---------|-----|--------|
| Render Dashboard | https://render.com/dashboard | Check logs |
| Vercel Dashboard | https://vercel.com/dashboard | Check build |
| Backend Health | https://prism-api.onrender.com/health | Should be 200 |
| Frontend | https://prism-ai-frontend.vercel.app | Should load |

---

## ✅ Success Indicators

After completing all steps:

- ✅ Backend health endpoint returns 200
- ✅ Frontend page loads without errors
- ✅ API calls from frontend succeed
- ✅ No CORS errors in browser console
- ✅ Database queries work
- ✅ All features functional
- ✅ Full stack LIVE and ready for users

---

## 🎉 You're Ready!

Follow these steps in order and your application will be live in 30 minutes!

**Start with Backend Setup → Frontend Setup → Connect Services → Verify**

---

**Status**: ✅ Complete setup guide ready

**Next Action**: Start with Backend Setup (Clear Cache & Redeploy)
