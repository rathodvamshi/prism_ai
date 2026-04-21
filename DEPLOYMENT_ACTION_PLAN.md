# 🎯 Deployment Action Plan - Step by Step

## 🔴 Issues Fixed

1. ✅ **Render**: Procfile fixed (uvicorn instead of gunicorn)
2. ✅ **Vercel**: Secret reference removed from vercel.json
3. ✅ **Both**: Complete setup guide created

---

## 🚀 Action Plan (30 Minutes Total)

### Phase 1: Backend (Render) - 20 Minutes

#### Step 1: Clear Cache (2 minutes)
```
1. Go to https://render.com/dashboard
2. Click "prism-api" service
3. Click "Settings" tab
4. Scroll to "Clear Build Cache"
5. Click "Clear" button
6. Confirm
```

#### Step 2: Manual Redeploy (1 minute)
```
1. Click "Deployments" tab
2. Click "Manual Deploy" button
3. Wait for build to start
```

#### Step 3: Monitor Build (15-20 minutes)
```
1. Click "Logs" tab
2. Watch for: "Uvicorn running on http://0.0.0.0:PORT"
3. Watch for: "✅ MongoDB warmed up"
4. Watch for: "✅ Redis warmed up"
5. Should NOT see: "gunicorn" or "uvicorn.workers" errors
```

#### Step 4: Verify Backend (1 minute)
```bash
curl https://prism-api.onrender.com/health
# Expected: {"status": "healthy", ...}
# Status: 200
```

**Backend URL**: `https://prism-api.onrender.com`

---

### Phase 2: Frontend (Vercel) - 5 Minutes

#### Step 1: Set Environment Variable (2 minutes)
```
1. Go to https://vercel.com/dashboard
2. Click "prism-ai-frontend" project
3. Click "Settings" tab
4. Click "Environment Variables"
5. Click "Add New"
6. Fill in:
   Name: VITE_API_URL
   Value: https://prism-api.onrender.com
   Environments: Production, Preview, Development
7. Click "Add"
```

#### Step 2: Redeploy (1 minute)
```
1. Click "Deployments" tab
2. Click "Redeploy" on latest deployment
3. Wait for build to complete
```

#### Step 3: Monitor Build (3-5 minutes)
```
1. Watch deployment status
2. Should see: "Ready" status
3. Should NOT see: "Build failed"
```

#### Step 4: Verify Frontend (1 minute)
```
1. Visit: https://prism-ai-frontend.vercel.app
2. Expected: Page loads without errors
3. Open DevTools: F12 → Console
4. Expected: No errors
```

**Frontend URL**: `https://prism-ai-frontend.vercel.app`

---

### Phase 3: Connect Services - 5 Minutes

#### Step 1: Update Backend CORS (2 minutes)
```
1. Go to https://render.com/dashboard
2. Click "prism-api" service
3. Click "Environment" tab
4. Find "CORS_ORIGINS"
5. Update value: https://prism-ai-frontend.vercel.app
6. Click "Save"
7. Wait for auto-redeploy (2-3 minutes)
```

#### Step 2: Verify Connection (1 minute)
```
1. Visit frontend: https://prism-ai-frontend.vercel.app
2. Open DevTools: F12 → Console
3. Run:
   fetch('https://prism-api.onrender.com/health')
     .then(r => r.json())
     .then(d => console.log('✅ Connected:', d))
     .catch(e => console.error('❌ Error:', e))
4. Expected: "✅ Connected: {status: "healthy", ...}"
5. Should NOT see: CORS errors
```

---

## ✅ Complete Checklist

### Backend (Render)
- [ ] Cache cleared
- [ ] Manual redeploy started
- [ ] Build completed (15-20 min)
- [ ] Logs show "Uvicorn running"
- [ ] No errors in logs
- [ ] Health endpoint returns 200
- [ ] Databases connected
- [ ] URL saved: https://prism-api.onrender.com

### Frontend (Vercel)
- [ ] Environment variable VITE_API_URL set
- [ ] Value: https://prism-api.onrender.com
- [ ] Environments: Production, Preview, Development
- [ ] Redeployed
- [ ] Build completed (3-5 min)
- [ ] Page loads without errors
- [ ] No console errors
- [ ] URL saved: https://prism-ai-frontend.vercel.app

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
0 min:    Start Backend Setup
0-2 min:  Clear cache
2-3 min:  Start redeploy
3-20 min: Build & deploy
20 min:   Backend LIVE ✅

20 min:   Start Frontend Setup
20-22 min: Set environment variable
22-23 min: Redeploy
23-28 min: Build & deploy
28 min:   Frontend LIVE ✅

28 min:   Start Connection Setup
28-30 min: Update CORS
30 min:   Full Stack LIVE ✅
```

**Total Time**: 30 minutes

---

## 🎯 Success Indicators

After completing all steps:

✅ Backend health endpoint returns 200
✅ Frontend page loads without errors
✅ API calls from frontend succeed
✅ No CORS errors in browser console
✅ Database queries work
✅ All features functional
✅ Full stack LIVE and ready for users

---

## 🚨 If Something Goes Wrong

### Backend Issues
- **Error**: "gunicorn app.main:app -k uvicorn"
  - **Fix**: Clear cache and redeploy
  - **Location**: Render Dashboard → Settings → Clear Build Cache

- **Error**: "Connection refused"
  - **Fix**: Check database URLs and IP whitelist
  - **Location**: MongoDB Atlas → Network Access

### Frontend Issues
- **Error**: "VITE_API_URL references Secret"
  - **Fix**: Already fixed! Set variable in Vercel dashboard
  - **Location**: Vercel Dashboard → Settings → Environment Variables

- **Error**: "Build failed"
  - **Fix**: Clear cache and reinstall
  - **Command**: `npm cache clean --force && npm install && npm run build`

### Connection Issues
- **Error**: "CORS error"
  - **Fix**: Update CORS_ORIGINS in Render
  - **Value**: https://prism-ai-frontend.vercel.app

---

## 📞 Reference Documents

| Document | Purpose |
|----------|---------|
| COMPLETE_DEPLOYMENT_SETUP.md | Detailed setup guide |
| RENDER_DEPLOYMENT_COMPLETE_FIX.md | Render-specific fixes |
| VERCEL_DEPLOYMENT_FIX.md | Vercel-specific fixes |
| DEPLOYMENT_ISSUES_SOLUTIONS.md | Common problems |
| BUILD_COMMANDS_REFERENCE.md | All build commands |

---

## 🎉 Ready to Deploy!

Everything is fixed and ready. Follow the action plan above and your application will be live in 30 minutes!

**Start Now**: Phase 1 - Backend Setup (Clear Cache & Redeploy)

---

**Status**: ✅ All fixes applied, ready for deployment

**Next Action**: Clear Render cache and redeploy NOW! ⚡
