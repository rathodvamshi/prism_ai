# 📋 Complete Deployment Checklist

## 🔴 CRITICAL - Must Complete Before Deployment

### Backend (Render)

#### Code & Configuration
- [ ] `app/__init__.py` exists (✅ Created)
- [ ] `requirements.txt` is up to date
- [ ] `Procfile` has correct start command (✅ Created)
- [ ] `runtime.txt` specifies Python 3.11.7 (✅ Created)
- [ ] `.env.production` template exists (✅ Created)
- [ ] No hardcoded secrets in code
- [ ] `.gitignore` excludes `.env` files
- [ ] All imports work: `python -c "from app.main import app"`

#### Database Setup
- [ ] MongoDB Atlas cluster created
- [ ] MongoDB IP whitelist includes: `0.0.0.0/0` (or Render IPs)
- [ ] MongoDB connection string tested locally
- [ ] Redis instance created (Redis Labs or similar)
- [ ] Redis connection string tested locally
- [ ] Neo4j Aura instance created
- [ ] Neo4j credentials verified
- [ ] Pinecone index created
- [ ] All database connections work locally

#### API Keys & Services
- [ ] Groq API key obtained and tested
- [ ] SendGrid API key obtained
- [ ] YouTube API key obtained
- [ ] JWT secret generated (any random string)
- [ ] Encryption key generated (base64 encoded)
- [ ] All API keys tested locally

#### Render Setup
- [ ] Render account created
- [ ] GitHub repository connected to Render
- [ ] Web Service created with correct settings
- [ ] All environment variables added to Render dashboard
- [ ] Build command verified: `pip install -r requirements.txt`
- [ ] Start command verified: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 4 --timeout 120`
- [ ] Instance type set to Standard (minimum)

#### Backend Verification
- [ ] Backend deploys without errors
- [ ] Health endpoint responds: `curl https://prism-api.onrender.com/health`
- [ ] No errors in Render logs
- [ ] Database connections working in production
- [ ] All services responding correctly

---

### Frontend (Vercel)

#### Code & Configuration
- [ ] `package.json` build script correct: `"build": "vite build"`
- [ ] `vite.config.ts` configured properly
- [ ] `.env.production` created with backend URL (✅ Created)
- [ ] `vercel.json` configured (✅ Created)
- [ ] No hardcoded API URLs (use env vars)
- [ ] `.gitignore` excludes node_modules (✅ Updated)
- [ ] Build succeeds locally: `npm run build`
- [ ] No TypeScript errors: `npm run lint`
- [ ] No console errors in dev mode

#### Vercel Setup
- [ ] Vercel account created
- [ ] GitHub repository connected to Vercel
- [ ] Project created with correct settings
- [ ] Build command: `npm run build`
- [ ] Output directory: `dist`
- [ ] Node version: 18.x
- [ ] Environment variable `VITE_API_URL` set to backend URL

#### Frontend Verification
- [ ] Frontend deploys without errors
- [ ] Page loads without console errors
- [ ] API calls to backend work
- [ ] No CORS errors in browser console
- [ ] All UI elements render correctly

---

## 🟡 IMPORTANT - Strongly Recommended

### Backend
- [ ] Celery worker service created (for background tasks)
- [ ] Celery beat service created (for scheduled tasks)
- [ ] Error logging configured
- [ ] Performance monitoring enabled
- [ ] Database backups configured
- [ ] Rate limiting configured
- [ ] Request timeout set appropriately

### Frontend
- [ ] Custom domain configured (if applicable)
- [ ] Analytics configured
- [ ] Error tracking configured (Sentry, etc.)
- [ ] Performance monitoring enabled
- [ ] SEO meta tags configured
- [ ] Favicon configured

---

## 🟢 NICE TO HAVE - Optional Enhancements

### Backend
- [ ] API documentation deployed (Swagger/OpenAPI)
- [ ] Health check monitoring set up
- [ ] Automated backups configured
- [ ] CDN configured for static files
- [ ] Database query optimization done
- [ ] Connection pooling optimized

### Frontend
- [ ] PWA manifest configured
- [ ] Service worker configured
- [ ] Lighthouse score optimized
- [ ] Bundle size analyzed and optimized
- [ ] Image optimization configured
- [ ] Caching strategy optimized

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Prepare Backend (30 minutes)
```bash
# 1. Update requirements
pip freeze > requirements.txt

# 2. Test locally
python -m uvicorn app.main:app --reload

# 3. Verify health endpoint
curl http://localhost:8000/health

# 4. Check for errors
python -m py_compile app/main.py

# 5. Commit and push
git add .
git commit -m "Prepare for production deployment"
git push origin main
```

### Step 2: Deploy Backend (10 minutes)
```
1. Go to render.com
2. Create Web Service
3. Add all environment variables
4. Wait for deployment
5. Test health endpoint
6. Check logs for errors
```

### Step 3: Prepare Frontend (20 minutes)
```bash
# 1. Update backend URL
# Edit Frontend/.env.production with backend URL

# 2. Build locally
cd Frontend
npm run build

# 3. Check for errors
npm run lint

# 4. Commit and push
git add .
git commit -m "Prepare frontend for production"
git push origin main
```

### Step 4: Deploy Frontend (5 minutes)
```
1. Go to vercel.com
2. Create Project
3. Add environment variable VITE_API_URL
4. Wait for deployment
5. Test page loads
6. Check console for errors
```

### Step 5: Verify Connection (5 minutes)
```bash
# 1. Test backend health
curl https://prism-api.onrender.com/health

# 2. Test frontend loads
curl https://your-frontend-name.vercel.app

# 3. Test API call from frontend
# Open browser console and run:
fetch('https://prism-api.onrender.com/health')
  .then(r => r.json())
  .then(d => console.log(d))

# 4. Check for CORS errors
# Open browser DevTools → Console
```

---

## 🔍 VERIFICATION TESTS

### Backend Tests
```bash
# 1. Health check
curl https://prism-api.onrender.com/health
# Expected: {"status": "healthy", ...}

# 2. Performance stats
curl https://prism-api.onrender.com/performance-stats
# Expected: Performance metrics

# 3. Celery health (if worker deployed)
curl https://prism-api.onrender.com/celery-health
# Expected: Celery status

# 4. Check logs
# Render Dashboard → Logs → View all logs
```

### Frontend Tests
```bash
# 1. Page loads
curl https://your-frontend-name.vercel.app
# Expected: HTML content

# 2. Check build
# Vercel Dashboard → Deployments → View logs

# 3. Browser console
# Open DevTools (F12) → Console
# Expected: No errors

# 4. Network requests
# DevTools → Network tab
# Expected: All requests succeed
```

### Integration Tests
```bash
# 1. API connectivity
# Browser console:
fetch('https://prism-api.onrender.com/health')
  .then(r => r.json())
  .then(d => console.log(d))

# 2. CORS headers
# DevTools → Network tab → click request → Headers
# Expected: Access-Control-Allow-Origin header present

# 3. Database connectivity
# Check Render logs for database connection messages
# Expected: "✅ MongoDB warmed up", "✅ Redis warmed up"
```

---

## 🆘 TROUBLESHOOTING

### If Backend Won't Deploy
1. Check Render logs immediately
2. Verify Python version: `python --version`
3. Test requirements locally: `pip install -r requirements.txt`
4. Check for syntax errors: `python -m py_compile app/main.py`
5. Verify all environment variables are set
6. Check database connections

### If Frontend Won't Deploy
1. Check Vercel build logs
2. Clear cache: `npm cache clean --force`
3. Reinstall: `rm -rf node_modules && npm install`
4. Check for TypeScript errors: `npm run lint`
5. Verify build command: `npm run build`

### If API Calls Fail
1. Verify backend is running: `curl https://prism-api.onrender.com/health`
2. Check CORS headers in browser Network tab
3. Verify `VITE_API_URL` is correct
4. Check backend logs for errors
5. Test with curl from command line

---

## 📊 MONITORING AFTER DEPLOYMENT

### Daily Checks
- [ ] Backend health endpoint responding
- [ ] Frontend page loads without errors
- [ ] API calls working
- [ ] No errors in logs
- [ ] Database connections stable

### Weekly Checks
- [ ] Review error logs
- [ ] Check performance metrics
- [ ] Monitor resource usage
- [ ] Verify backups working
- [ ] Check for security issues

### Monthly Checks
- [ ] Update dependencies
- [ ] Review security advisories
- [ ] Optimize performance
- [ ] Review costs
- [ ] Plan capacity upgrades

---

## 🔐 SECURITY CHECKLIST

- [ ] No secrets in code
- [ ] `.env` files in `.gitignore`
- [ ] HTTPS enabled (automatic on Vercel/Render)
- [ ] CORS properly configured
- [ ] JWT secret strong and unique
- [ ] Database credentials secure
- [ ] API keys rotated regularly
- [ ] Rate limiting enabled
- [ ] Input validation implemented
- [ ] SQL injection prevention implemented

---

## ✅ FINAL SIGN-OFF

- [ ] All critical items completed
- [ ] Backend deployed and verified
- [ ] Frontend deployed and verified
- [ ] Integration tested
- [ ] Monitoring configured
- [ ] Team notified
- [ ] Documentation updated
- [ ] Ready for production traffic

---

## 📞 SUPPORT CONTACTS

- **Render Support**: https://render.com/support
- **Vercel Support**: https://vercel.com/support
- **FastAPI Issues**: https://github.com/tiangolo/fastapi/issues
- **Vite Issues**: https://github.com/vitejs/vite/issues

---

## 📝 NOTES

- Deployment time: ~30-45 minutes total
- Most common issues: Environment variables, CORS, database connections
- Always test locally before deploying
- Keep backups of database
- Monitor logs regularly
- Update dependencies monthly
