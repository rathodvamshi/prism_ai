# ⚡ Deployment Quick Reference Card

## 🚀 30-Second Overview

```
FRONTEND (Vercel)          BACKEND (Render)
├─ React + Vite            ├─ FastAPI + Gunicorn
├─ Build: npm run build    ├─ Build: pip install -r requirements.txt
├─ Output: dist/           ├─ Start: gunicorn app.main:app ...
└─ Env: VITE_API_URL       └─ Env: 25+ variables
```

---

## 📋 Deployment Checklist (Copy-Paste)

### Backend (Render)
```
☐ Create Web Service
☐ Set Build Command: pip install -r requirements.txt
☐ Set Start Command: gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 4 --timeout 120
☐ Add all environment variables (see ENVIRONMENT_VARIABLES_GUIDE.md)
☐ Deploy
☐ Test: curl https://prism-api.onrender.com/health
```

### Frontend (Vercel)
```
☐ Create Project
☐ Set Build Command: npm run build
☐ Set Output Directory: dist
☐ Add VITE_API_URL environment variable
☐ Deploy
☐ Test: Visit Vercel URL
```

---

## 🔑 Essential Environment Variables

### Backend (Render Dashboard)
```
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend-name.vercel.app
GROQ_API_KEY=<your-key>
REDIS_URL=<your-url>
MONGO_URI=<your-uri>
NEO4J_URI=<your-uri>
NEO4J_USER=<your-user>
NEO4J_PASSWORD=<your-password>
PINECONE_API_KEY=<your-key>
SENDGRID_API_KEY=<your-key>
SENDER_EMAIL=<your-email>
YOUTUBE_API_KEY=<your-key>
JWT_SECRET=<any-random-string>
ENCRYPTION_KEY=<base64-encoded-key>
CELERY_BROKER_URL=<your-redis-url>
CELERY_RESULT_BACKEND=<your-redis-url>
```

### Frontend (Vercel Dashboard)
```
VITE_API_URL=https://prism-api.onrender.com
```

---

## 🧪 Quick Tests

### Backend Health
```bash
curl https://prism-api.onrender.com/health
# Expected: {"status": "healthy", ...}
```

### Frontend Loads
```bash
curl https://your-frontend-name.vercel.app
# Expected: HTML content
```

### API Connectivity (Browser Console)
```javascript
fetch('https://prism-api.onrender.com/health')
  .then(r => r.json())
  .then(d => console.log(d))
```

---

## 🆘 Emergency Fixes

### Backend Won't Start
```
1. Check Render logs
2. Verify all env vars set
3. Test locally: python -m uvicorn app.main:app --reload
4. Check requirements.txt
```

### Frontend Won't Build
```
1. Check Vercel logs
2. Clear cache: npm cache clean --force
3. Reinstall: rm -rf node_modules && npm install
4. Test locally: npm run build
```

### API Calls Fail
```
1. Check backend running: curl https://prism-api.onrender.com/health
2. Check CORS in browser Network tab
3. Verify VITE_API_URL correct
4. Check backend logs
```

---

## 📊 File Structure

```
project/
├── Frontend/
│   ├── .env.production ✅ (created)
│   ├── vercel.json ✅ (created)
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│
├── prism-backend/
│   ├── Procfile ✅ (created)
│   ├── runtime.txt ✅ (created)
│   ├── .env.production ✅ (created)
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py ✅ (created)
│   │   └── main.py
│   └── render.yaml
│
└── Documentation/
    ├── DEPLOYMENT_GUIDE.md ✅
    ├── QUICK_DEPLOYMENT_SETUP.md ✅
    ├── DEPLOYMENT_CHECKLIST.md ✅
    ├── DEPLOYMENT_ISSUES_SOLUTIONS.md ✅
    ├── ENVIRONMENT_VARIABLES_GUIDE.md ✅
    ├── DEPLOYMENT_SUMMARY.md ✅
    └── DEPLOYMENT_QUICK_REFERENCE.md ✅ (this file)
```

---

## 🔗 Important URLs

| Service | URL |
|---------|-----|
| Render Dashboard | https://render.com/dashboard |
| Vercel Dashboard | https://vercel.com/dashboard |
| MongoDB Atlas | https://cloud.mongodb.com |
| Redis Labs | https://redis.com |
| Neo4j Aura | https://neo4j.com/cloud/aura |
| Pinecone | https://app.pinecone.io |
| SendGrid | https://sendgrid.com |
| Groq Console | https://console.groq.com |

---

## ⏱️ Time Estimates

| Task | Time |
|------|------|
| Gather API keys | 15 min |
| Deploy backend | 10 min |
| Deploy frontend | 5 min |
| Test integration | 5 min |
| **Total** | **35 min** |

---

## 🎯 Success Indicators

✅ Backend health endpoint returns 200
✅ Frontend page loads without errors
✅ API calls from frontend succeed
✅ No CORS errors in browser console
✅ Database queries work
✅ Static files load correctly

---

## 📞 Support Resources

| Issue | Resource |
|-------|----------|
| Render Help | https://render.com/support |
| Vercel Help | https://vercel.com/support |
| FastAPI Docs | https://fastapi.tiangolo.com |
| Vite Docs | https://vitejs.dev |
| MongoDB Docs | https://docs.mongodb.com |
| Redis Docs | https://redis.io/docs |

---

## 🔐 Security Reminders

- ✅ Never commit `.env` files
- ✅ Use strong JWT secret (32+ chars)
- ✅ Rotate API keys regularly
- ✅ Keep encryption key safe
- ✅ Monitor logs for suspicious activity
- ✅ Use HTTPS only (automatic on Vercel/Render)

---

## 📝 Common Commands

### Backend
```bash
# Test locally
python -m uvicorn app.main:app --reload

# Check requirements
pip install -r requirements.txt

# Verify imports
python -c "from app.main import app"
```

### Frontend
```bash
# Build
npm run build

# Lint
npm run lint

# Preview build
npm run preview
```

---

## 🚨 Critical Paths

### If Backend Fails
1. Check Render logs immediately
2. Verify environment variables
3. Test locally
4. Check database connections
5. Rollback if needed

### If Frontend Fails
1. Check Vercel build logs
2. Clear cache and reinstall
3. Check for TypeScript errors
4. Test locally
5. Rollback if needed

### If Integration Fails
1. Verify backend running
2. Check CORS headers
3. Verify API URL correct
4. Check browser console
5. Test with curl

---

## 📊 Monitoring Dashboard

### Render
- Dashboard → Logs (check for errors)
- Dashboard → Metrics (CPU, Memory, Network)
- Dashboard → Events (deployment history)

### Vercel
- Dashboard → Deployments (build status)
- Dashboard → Analytics (performance)
- Dashboard → Logs (build and runtime logs)

---

## 🎓 Learning Resources

- **Render Docs**: https://render.com/docs
- **Vercel Docs**: https://vercel.com/docs
- **FastAPI Tutorial**: https://fastapi.tiangolo.com/tutorial/
- **Vite Guide**: https://vitejs.dev/guide/
- **12 Factor App**: https://12factor.net/

---

## ✅ Final Checklist

- [ ] All API keys obtained
- [ ] Databases created and accessible
- [ ] GitHub connected to Render and Vercel
- [ ] Backend configuration files created
- [ ] Frontend configuration files created
- [ ] Documentation reviewed
- [ ] Ready to deploy

---

## 🎉 Ready to Deploy!

**Next Step**: Read `QUICK_DEPLOYMENT_SETUP.md` for 5-minute deployment

**Questions?**: Check the relevant documentation file

**Issues?**: See `DEPLOYMENT_ISSUES_SOLUTIONS.md`

---

**Status**: ✅ All systems ready for deployment
**Last Updated**: April 22, 2026
