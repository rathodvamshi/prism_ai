# Common Deployment Issues & Solutions

## 🔴 CRITICAL ISSUES

### 1. **Module Import Errors on Render**

**Error**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Ensure app directory has __init__.py
touch prism-backend/app/__init__.py

# Verify requirements.txt includes all dependencies
pip freeze > requirements.txt

# Check Procfile uses correct module path
# Should be: gunicorn app.main:app
```

---

### 2. **Database Connection Timeout**

**Error**: `Connection timeout to MongoDB/Redis/Neo4j`

**Solution**:
```python
# In .env.production, increase timeouts:
MONGODB_TIMEOUT_MS=10000
NEO4J_TIMEOUT_MS=20000
REDIS_TIMEOUT_MS=1000

# Verify IP whitelist in MongoDB Atlas:
# 1. Go to MongoDB Atlas → Network Access
# 2. Add Render's IP range: 0.0.0.0/0 (or specific Render IPs)
# 3. Or use connection string with proper credentials
```

---

### 3. **CORS Errors in Frontend**

**Error**: `Access to XMLHttpRequest blocked by CORS policy`

**Solution**:
```python
# In backend .env.production:
CORS_ORIGINS=https://your-frontend-name.vercel.app,https://www.your-domain.com

# Verify in app/main.py CORS middleware:
CORSMiddleware(
    app,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 4. **Celery Worker Not Starting**

**Error**: `Worker failed to start` or `Connection refused`

**Solution**:
```bash
# Verify Redis URL format:
# Should be: rediss://user:password@host:port (note: rediss with 's' for SSL)

# In Render, set both:
CELERY_BROKER_URL=rediss://user:password@host:port
CELERY_RESULT_BACKEND=rediss://user:password@host:port

# Test Redis connection:
redis-cli -u rediss://user:password@host:port ping
```

---

### 5. **Frontend Build Fails on Vercel**

**Error**: `Build failed` or `npm ERR!`

**Solution**:
```bash
# Clear cache and rebuild locally
rm -rf node_modules dist
npm install
npm run build

# Check for TypeScript errors
npm run lint

# Verify package.json has correct build script:
"build": "vite build"

# In Vercel, set Node version to 18.x
```

---

## ⚠️ COMMON ISSUES

### 6. **Environment Variables Not Loading**

**Error**: `KeyError: 'GROQ_API_KEY'` or similar

**Solution**:
```python
# Verify in Render dashboard all vars are set
# Check .env.production has all required variables
# Verify variable names match exactly (case-sensitive)

# In Python, use:
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    groq_api_key: str = ""  # with default
```

---

### 7. **Port Already in Use**

**Error**: `Address already in use` or `Port 8000 in use`

**Solution**:
```bash
# Render automatically assigns PORT via environment variable
# Ensure Procfile uses: --bind 0.0.0.0:$PORT

# Don't hardcode port:
# ❌ WRONG: gunicorn app.main:app --bind 0.0.0.0:8000
# ✅ RIGHT: gunicorn app.main:app --bind 0.0.0.0:$PORT
```

---

### 8. **Static Files Not Serving**

**Error**: `404 Not Found` for CSS/JS files

**Solution**:
```json
// In vercel.json, ensure rewrites are correct:
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}

// Verify build output directory is 'dist'
// Check vite.config.ts has correct build config
```

---

### 9. **API Calls Return 502 Bad Gateway**

**Error**: `502 Bad Gateway` from Render

**Solution**:
```bash
# Check Render logs for actual error
# Verify all database connections are working
# Check if service is crashing on startup

# Increase startup timeout:
STARTUP_TIMEOUT_SECONDS=60

# Check Procfile timeout:
gunicorn ... --timeout 120
```

---

### 10. **Memory Issues on Render**

**Error**: `Killed` or `Out of memory`

**Solution**:
```bash
# Upgrade Render instance type (Standard → Pro)
# Reduce Celery concurrency:
celery -A app.core.celery_app worker --concurrency=2

# Optimize database queries
# Enable connection pooling
# Monitor memory usage in Render dashboard
```

---

## 🔧 VERIFICATION STEPS

### Backend Verification

```bash
# 1. Check service is running
curl https://prism-api.onrender.com/health

# 2. Check performance stats
curl https://prism-api.onrender.com/performance-stats

# 3. Check Celery health (if worker deployed)
curl https://prism-api.onrender.com/celery-health

# 4. Check logs
# Render Dashboard → Logs → View all logs
```

### Frontend Verification

```bash
# 1. Check build succeeded
# Vercel Dashboard → Deployments → View logs

# 2. Check environment variables loaded
# Open browser console → check for API URL

# 3. Test API connectivity
# In browser console:
fetch('https://prism-api.onrender.com/health')
  .then(r => r.json())
  .then(d => console.log(d))

# 4. Check for CORS errors
# Browser console → Network tab → check headers
```

---

## 📋 PRE-DEPLOYMENT CHECKLIST

### Backend
- [ ] `requirements.txt` updated with all dependencies
- [ ] `Procfile` has correct start command
- [ ] `runtime.txt` specifies Python 3.11.7
- [ ] `.env.production` template created
- [ ] All environment variables documented
- [ ] Database connections tested locally
- [ ] Health endpoint working locally
- [ ] No hardcoded secrets in code
- [ ] `.gitignore` excludes `.env` files

### Frontend
- [ ] `package.json` build script correct
- [ ] `vite.config.ts` configured properly
- [ ] `.env.production` created with backend URL
- [ ] No hardcoded API URLs (use env vars)
- [ ] Build succeeds locally: `npm run build`
- [ ] No console errors in dev mode
- [ ] `vercel.json` configured
- [ ] `.gitignore` excludes node_modules

---

## 🚨 EMERGENCY FIXES

### If Backend Won't Start

1. Check Render logs immediately
2. Verify Python version: `python --version`
3. Test requirements locally: `pip install -r requirements.txt`
4. Check for syntax errors: `python -m py_compile app/main.py`
5. Rollback to previous commit if needed

### If Frontend Won't Build

1. Check Vercel build logs
2. Clear cache: `npm cache clean --force`
3. Reinstall: `rm -rf node_modules && npm install`
4. Check for TypeScript errors: `npm run lint`
5. Rollback to previous commit if needed

### If API Calls Fail

1. Verify backend is running: `curl https://prism-api.onrender.com/health`
2. Check CORS headers in browser Network tab
3. Verify `VITE_API_URL` is correct in Vercel env vars
4. Check backend logs for errors
5. Test with curl from command line

---

## 📞 GETTING HELP

1. **Check Render Logs**: Dashboard → Logs → View all logs
2. **Check Vercel Logs**: Dashboard → Deployments → View logs
3. **Check Browser Console**: F12 → Console tab
4. **Check Network Tab**: F12 → Network tab → check failed requests
5. **Test Locally**: Ensure everything works locally before deploying

---

## ✅ SUCCESS INDICATORS

- ✅ Backend health endpoint returns 200
- ✅ Frontend loads without console errors
- ✅ API calls from frontend succeed
- ✅ No CORS errors in browser
- ✅ Database queries work
- ✅ Celery tasks execute (if applicable)
- ✅ Static files load correctly
- ✅ Custom domain works (if configured)
