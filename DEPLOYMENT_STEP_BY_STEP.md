# 🚀 Complete Step-by-Step Deployment Guide

## 📋 Table of Contents
1. [Pre-Deployment Setup](#pre-deployment-setup)
2. [Backend Deployment (Render)](#backend-deployment-render)
3. [Frontend Deployment (Vercel)](#frontend-deployment-vercel)
4. [Connect Frontend to Backend](#connect-frontend-to-backend)
5. [Verification & Testing](#verification--testing)
6. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Setup

### Step 1: Verify Local Build Works

#### Backend
```bash
# Navigate to backend directory
cd prism-backend

# Install dependencies
pip install -r requirements.txt

# Test if app imports correctly
python -c "from app.main import app; print('✅ Backend imports successfully')"

# Run locally to verify
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# Expected: Uvicorn running on http://127.0.0.1:8000
# Press Ctrl+C to stop
```

#### Frontend
```bash
# Navigate to frontend directory
cd Frontend

# Install dependencies
npm install

# Build the project
npm run build

# Expected output: dist/ folder created with optimized files

# Preview the build
npm run preview
# Expected: Preview server running on http://localhost:4173
# Press Ctrl+C to stop
```

### Step 2: Verify Environment Variables

#### Backend - Check `.env` file
```bash
# In prism-backend/.env, verify these exist:
cat prism-backend/.env | grep -E "GROQ_API_KEY|MONGO_URI|REDIS_URL|NEO4J_URI"
```

#### Frontend - Check `.env.production`
```bash
# In Frontend/.env.production, verify:
cat Frontend/.env.production
# Should show: VITE_API_URL=http://localhost:8000 (for local testing)
```

---

## Backend Deployment (Render)

### Step 1: Create Render Account

1. Go to **https://render.com**
2. Click **"Sign Up"**
3. Use GitHub account to sign up (recommended)
4. Authorize Render to access your GitHub

### Step 2: Connect GitHub Repository

1. In Render Dashboard, click **"New +"**
2. Select **"Web Service"**
3. Click **"Connect a repository"**
4. Search for **"prism_ai"**
5. Click **"Connect"**

### Step 3: Configure Web Service

Fill in the following:

```
Name:                    prism-api
Environment:             Python 3
Build Command:           pip install -r requirements.txt
Start Command:           python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
Instance Type:           Standard
Region:                  (Choose closest to you)
Branch:                  main
Auto-deploy:             Yes
```

### Step 4: Add Environment Variables

Click **"Environment"** and add each variable:

#### Critical Variables (Must Have)
```
ENVIRONMENT                 production
CORS_ORIGINS                https://your-frontend-name.vercel.app
```

#### AI/LLM Services
```
GROQ_API_KEY                gsk_xxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY              sk_xxxxxxxxxxxxxxxxxxxxx (optional)
```

#### Database URLs
```
REDIS_URL                   rediss://user:password@host:port
MONGO_URI                   mongodb+srv://user:password@cluster.mongodb.net/prismdb?retryWrites=true&w=majority
```

#### Neo4j Configuration
```
NEO4J_URI                   neo4j+s://xxxxx.databases.neo4j.io:7687
NEO4J_USER                  xxxxxxxxxxxxx
NEO4J_PASSWORD              xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NEO4J_DATABASE              neo4j
NEO4J_ENCRYPTED             true
NEO4J_MAX_POOL_SIZE         50
NEO4J_CONNECTION_TIMEOUT    30
NEO4J_TRUST                 TRUST_ALL_CERTIFICATES
NEO4J_RETRY_ATTEMPTS        3
NEO4J_RETRY_DELAY           1
```

#### Pinecone & Media
```
PINECONE_API_KEY            pcsk_xxxxxxxxxxxxxxxxxxxxx
YOUTUBE_API_KEY             AIzaSyxxxxxxxxxxxxxxxxxxxxx
MEDIA_DEFAULT_MODE          redirect
MEDIA_CACHE_TTL             172800
MEDIA_USE_SCRAPER_FALLBACK  true
```

#### Email Service
```
SENDGRID_API_KEY            SG.xxxxxxxxxxxxxxxxxxxxx
SENDER_EMAIL                your-email@example.com
```

#### Security
```
JWT_SECRET                  your-random-secret-string-here
ENCRYPTION_KEY              5Q_PSus1BJ80iJtiLS6ZhjhFHY2vmjPWJHv8lm-41oU=
```

#### Celery Configuration
```
CELERY_BROKER_URL           rediss://user:password@host:port
CELERY_RESULT_BACKEND       rediss://user:password@host:port
```

#### Connection Settings
```
ENABLE_CONNECTION_MONITORING    true
CONNECTION_HEALTH_CHECK_INTERVAL 60
CONNECTION_RETRY_BACKOFF        exponential
LOG_CONNECTION_EVENTS           false
REDIS_TIMEOUT_MS                500
MONGODB_TIMEOUT_MS              5000
NEO4J_TIMEOUT_MS                15000
PINECONE_TIMEOUT_MS             8000
STARTUP_TIMEOUT_SECONDS         30
DEFER_DB_VALIDATION             true
ENABLE_GRACEFUL_DEGRADATION     true
```

### Step 5: Deploy Backend

1. Click **"Create Web Service"**
2. Wait for build to complete (5-10 minutes)
3. Check logs for errors:
   - Click **"Logs"** tab
   - Look for: `✅ MongoDB warmed up`, `✅ Redis warmed up`
   - Should NOT see: `❌ Error`, `Connection refused`

### Step 6: Get Backend URL

Once deployed:
1. Go to **"Settings"** tab
2. Copy the **"Render URL"** (e.g., `https://prism-api.onrender.com`)
3. Save this URL - you'll need it for frontend

### Step 7: Test Backend Health

```bash
# Test the health endpoint
curl https://prism-api.onrender.com/health

# Expected response:
# {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z", ...}

# If you get 502 Bad Gateway:
# 1. Check Render logs
# 2. Verify all environment variables are set
# 3. Wait 2-3 minutes for service to fully start
```

---

## Frontend Deployment (Vercel)

### Step 1: Create Vercel Account

1. Go to **https://vercel.com**
2. Click **"Sign Up"**
3. Use GitHub account (recommended)
4. Authorize Vercel to access your GitHub

### Step 2: Import Project

1. In Vercel Dashboard, click **"Add New"**
2. Select **"Project"**
3. Click **"Import Git Repository"**
4. Search for **"prism_ai"**
5. Click **"Import"**

### Step 3: Configure Project

In the import dialog, fill in:

```
Project Name:           prism-ai-frontend
Framework Preset:       Vite
Root Directory:         Frontend
Build Command:          npm run build
Output Directory:       dist
Install Command:        npm install
```

### Step 4: Add Environment Variables

Before deploying, add environment variables:

1. Click **"Environment Variables"**
2. Add:
   ```
   Name:           VITE_API_URL
   Value:          https://prism-api.onrender.com
   Environments:   Production, Preview, Development
   ```
3. Click **"Add"**

### Step 5: Deploy Frontend

1. Click **"Deploy"**
2. Wait for build to complete (3-5 minutes)
3. Check build logs:
   - Should see: `✅ Build completed`
   - Should NOT see: `❌ Build failed`

### Step 6: Get Frontend URL

Once deployed:
1. You'll see a success message with your URL
2. URL format: `https://prism-ai-frontend.vercel.app`
3. Save this URL

### Step 7: Test Frontend

```bash
# Visit your frontend URL in browser
https://prism-ai-frontend.vercel.app

# Expected:
# - Page loads without errors
# - No console errors (F12 → Console)
# - UI renders correctly
```

---

## Connect Frontend to Backend

### Step 1: Update Backend CORS

Now that you have your frontend URL, update backend CORS:

1. Go to **Render Dashboard**
2. Select **"prism-api"** service
3. Go to **"Environment"**
4. Find **"CORS_ORIGINS"**
5. Update value to:
   ```
   https://prism-ai-frontend.vercel.app
   ```
6. Click **"Save"**
7. Service will auto-redeploy (2-3 minutes)

### Step 2: Update Frontend API URL

1. Go to **Vercel Dashboard**
2. Select **"prism-ai-frontend"** project
3. Go to **"Settings"** → **"Environment Variables"**
4. Find **"VITE_API_URL"**
5. Update value to:
   ```
   https://prism-api.onrender.com
   ```
6. Click **"Save"**
7. Go to **"Deployments"**
8. Click **"Redeploy"** on latest deployment
9. Wait for build to complete

### Step 3: Verify Connection

```bash
# Test backend is accessible
curl https://prism-api.onrender.com/health

# Test frontend loads
curl https://prism-ai-frontend.vercel.app

# Both should return 200 status
```

---

## Verification & Testing

### Test 1: Backend Health Check

```bash
# Check backend is running
curl -X GET https://prism-api.onrender.com/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "0.1.0"
}
```

### Test 2: Frontend Loads

```bash
# Check frontend loads
curl -I https://prism-ai-frontend.vercel.app

# Expected response:
# HTTP/2 200
# content-type: text/html
```

### Test 3: API Connectivity (Browser Console)

1. Open your frontend URL in browser
2. Press **F12** to open DevTools
3. Go to **"Console"** tab
4. Run this command:

```javascript
fetch('https://prism-api.onrender.com/health')
  .then(r => r.json())
  .then(d => console.log('✅ Backend connected:', d))
  .catch(e => console.error('❌ Connection failed:', e))
```

Expected output:
```
✅ Backend connected: {status: "healthy", ...}
```

### Test 4: Check CORS Headers

1. In DevTools, go to **"Network"** tab
2. Refresh the page
3. Click on any API request
4. Go to **"Headers"** tab
5. Look for:
   ```
   Access-Control-Allow-Origin: https://prism-ai-frontend.vercel.app
   Access-Control-Allow-Credentials: true
   ```

### Test 5: Database Connectivity

Check backend logs to verify databases are connected:

1. Go to **Render Dashboard**
2. Select **"prism-api"**
3. Go to **"Logs"**
4. Look for:
   ```
   ✅ MongoDB warmed up
   ✅ Redis warmed up
   ✅ Neo4j warmed up
   ```

---

## Build Commands Reference

### Backend Build Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "fastapi|uvicorn|gunicorn"

# Test imports
python -c "from app.main import app; print('OK')"

# Run locally
python -m uvicorn app.main:app --reload

# Run with gunicorn (production)
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4

# Check syntax
python -m py_compile app/main.py

# Run tests (if available)
pytest tests/
```

### Frontend Build Commands

```bash
# Install dependencies
npm install

# Check for vulnerabilities
npm audit

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint

# Check TypeScript
npx tsc --noEmit

# Clean build
rm -rf node_modules dist
npm install
npm run build
```

---

## Environment Variables Checklist

### Backend (Render)
- [ ] ENVIRONMENT = production
- [ ] CORS_ORIGINS = https://your-frontend-url
- [ ] GROQ_API_KEY = set
- [ ] REDIS_URL = set
- [ ] MONGO_URI = set
- [ ] NEO4J_URI = set
- [ ] NEO4J_USER = set
- [ ] NEO4J_PASSWORD = set
- [ ] PINECONE_API_KEY = set
- [ ] SENDGRID_API_KEY = set
- [ ] SENDER_EMAIL = set
- [ ] YOUTUBE_API_KEY = set
- [ ] JWT_SECRET = set
- [ ] ENCRYPTION_KEY = set
- [ ] CELERY_BROKER_URL = set
- [ ] CELERY_RESULT_BACKEND = set

### Frontend (Vercel)
- [ ] VITE_API_URL = https://prism-api.onrender.com

---

## Troubleshooting

### Backend Won't Start

**Error**: `502 Bad Gateway`

**Solution**:
```bash
# 1. Check Render logs
# Render Dashboard → prism-api → Logs

# 2. Verify environment variables
# Render Dashboard → prism-api → Environment
# Make sure all variables are set

# 3. Test locally
cd prism-backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# 4. Check Python version
python --version
# Should be 3.11+

# 5. Check requirements.txt
cat requirements.txt | head -20

# 6. Verify Procfile
cat prism-backend/Procfile
```

### Frontend Build Fails

**Error**: `Build failed`

**Solution**:
```bash
# 1. Check Vercel logs
# Vercel Dashboard → prism-ai-frontend → Deployments → View logs

# 2. Clear cache and rebuild locally
cd Frontend
rm -rf node_modules dist
npm cache clean --force
npm install
npm run build

# 3. Check for TypeScript errors
npm run lint

# 4. Check package.json
cat package.json | grep -A 5 '"scripts"'

# 5. Verify build command
# Should be: npm run build
```

### API Calls Fail

**Error**: `CORS error` or `Connection refused`

**Solution**:
```bash
# 1. Verify backend is running
curl https://prism-api.onrender.com/health

# 2. Check CORS_ORIGINS in backend
# Render Dashboard → prism-api → Environment
# CORS_ORIGINS should include your frontend URL

# 3. Check VITE_API_URL in frontend
# Vercel Dashboard → prism-ai-frontend → Settings → Environment Variables
# VITE_API_URL should be https://prism-api.onrender.com

# 4. Check browser console (F12)
# Look for CORS error messages

# 5. Redeploy both services
# Render: Click "Manual Deploy"
# Vercel: Click "Redeploy"
```

### Database Connection Error

**Error**: `Connection timeout` or `Connection refused`

**Solution**:
```bash
# 1. Verify connection strings
# Check MongoDB Atlas IP whitelist includes Render IPs
# MongoDB Atlas → Network Access → Add 0.0.0.0/0

# 2. Test connection locally
# Update .env with production URLs
# python -c "from app.db.mongo_client import db; print('OK')"

# 3. Check Render logs for connection errors
# Render Dashboard → prism-api → Logs

# 4. Verify credentials
# Make sure username and password are correct
# Check for special characters that need URL encoding
```

---

## Monitoring After Deployment

### Daily Checks

```bash
# Check backend health
curl https://prism-api.onrender.com/health

# Check frontend loads
curl -I https://prism-ai-frontend.vercel.app

# Check logs
# Render Dashboard → Logs
# Vercel Dashboard → Deployments → Logs
```

### Weekly Checks

```bash
# Review error logs
# Check database performance
# Monitor API usage
# Check for security issues
```

### Monthly Checks

```bash
# Update dependencies
pip list --outdated
npm outdated

# Review security advisories
pip audit
npm audit

# Optimize performance
# Check bundle size
# Review database queries
```

---

## Success Indicators

After deployment, you should see:

✅ Backend health endpoint returns 200
✅ Frontend page loads without errors
✅ API calls from frontend succeed
✅ No CORS errors in browser console
✅ Database queries work
✅ Static files load correctly
✅ No console errors
✅ Performance is acceptable

---

## Quick Reference URLs

| Service | URL |
|---------|-----|
| Render Dashboard | https://render.com/dashboard |
| Vercel Dashboard | https://vercel.com/dashboard |
| Backend Health | https://prism-api.onrender.com/health |
| Frontend | https://prism-ai-frontend.vercel.app |
| GitHub Repo | https://github.com/rathodvamshi/prism_ai |

---

## Next Steps

1. ✅ Deploy backend to Render
2. ✅ Deploy frontend to Vercel
3. ✅ Connect them together
4. ✅ Test integration
5. ✅ Monitor logs
6. ✅ Configure custom domain (optional)
7. ✅ Set up monitoring alerts (optional)

---

**Estimated Total Time**: 30-45 minutes

**You're ready to deploy!** 🚀
