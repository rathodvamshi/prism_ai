# ⚡ Quick Deployment Setup (5 Minutes)

## 🎯 What You Need Before Starting

1. **Render Account** - https://render.com (free tier available)
2. **Vercel Account** - https://vercel.com (free tier available)
3. **GitHub Repository** - Connected to both services
4. **API Keys Ready**:
   - Groq API Key
   - MongoDB Atlas Connection String
   - Redis URL (from Redis Labs or similar)
   - Neo4j Aura Credentials
   - Pinecone API Key
   - SendGrid API Key
   - YouTube API Key
   - JWT Secret (any random string)
   - Encryption Key (base64 encoded)

---

## 🚀 BACKEND DEPLOYMENT (Render) - 3 Minutes

### 1. Create Web Service
```
1. Go to render.com → Dashboard
2. Click "New +" → "Web Service"
3. Select your GitHub repository
4. Fill in:
   - Name: prism-api
   - Environment: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 4 --timeout 120
   - Instance Type: Standard
5. Click "Create Web Service"
```

### 2. Add Environment Variables (Copy-Paste)
Go to Service Settings → Environment Variables → Add:

```
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend-name.vercel.app
GROQ_API_KEY=<paste-your-groq-key>
REDIS_URL=<paste-your-redis-url>
MONGO_URI=<paste-your-mongodb-uri>
NEO4J_URI=<paste-your-neo4j-uri>
NEO4J_USER=<paste-your-neo4j-user>
NEO4J_PASSWORD=<paste-your-neo4j-password>
NEO4J_DATABASE=<paste-your-neo4j-database>
PINECONE_API_KEY=<paste-your-pinecone-key>
SENDGRID_API_KEY=<paste-your-sendgrid-key>
SENDER_EMAIL=<paste-your-sender-email>
YOUTUBE_API_KEY=<paste-your-youtube-key>
JWT_SECRET=<paste-any-random-string>
ENCRYPTION_KEY=<paste-your-encryption-key>
CELERY_BROKER_URL=<paste-your-redis-url>
CELERY_RESULT_BACKEND=<paste-your-redis-url>
```

### 3. Wait for Deployment
- Render will automatically build and deploy
- Check logs for any errors
- Once deployed, you'll get a URL like: `https://prism-api.onrender.com`

### 4. Test Backend
```bash
curl https://prism-api.onrender.com/health
# Should return: {"status": "healthy", ...}
```

---

## 🎨 FRONTEND DEPLOYMENT (Vercel) - 2 Minutes

### 1. Deploy to Vercel
```
1. Go to vercel.com → Dashboard
2. Click "Add New..." → "Project"
3. Select your GitHub repository
4. Select "Frontend" folder as root
5. Framework: Vite
6. Build Command: npm run build
7. Output Directory: dist
8. Click "Deploy"
```

### 2. Add Environment Variable
Go to Project Settings → Environment Variables:

```
Name: VITE_API_URL
Value: https://prism-api.onrender.com
Environments: Production, Preview, Development
```

### 3. Redeploy
- Go to Deployments → Click "Redeploy" on latest deployment
- Wait for build to complete

### 4. Test Frontend
- Visit your Vercel URL
- Open browser console (F12)
- Should see no errors
- API calls should work

---

## ✅ VERIFICATION CHECKLIST

### Backend
- [ ] Service deployed on Render
- [ ] All environment variables set
- [ ] Health endpoint returns 200: `curl https://prism-api.onrender.com/health`
- [ ] No errors in Render logs

### Frontend
- [ ] Project deployed on Vercel
- [ ] Environment variable set
- [ ] Build succeeded
- [ ] Page loads without errors
- [ ] Browser console shows no errors

### Connection
- [ ] Frontend can reach backend
- [ ] No CORS errors in browser console
- [ ] API calls work from frontend

---

## 🔧 COMMON QUICK FIXES

### Backend Won't Start
```bash
# Check logs in Render Dashboard
# Most common issues:
1. Missing environment variable → Add it in dashboard
2. Database connection error → Verify connection string
3. Python version mismatch → Check runtime.txt
```

### Frontend Build Fails
```bash
# Check logs in Vercel Dashboard
# Most common issues:
1. Missing dependency → npm install locally first
2. TypeScript error → npm run lint locally
3. Wrong build command → Verify in vercel.json
```

### API Calls Fail
```bash
# Check browser console (F12)
# Most common issues:
1. CORS error → Update CORS_ORIGINS in backend
2. Wrong API URL → Update VITE_API_URL in frontend
3. Backend down → Check Render dashboard
```

---

## 📱 AFTER DEPLOYMENT

### Monitor Your Services
- **Render**: Dashboard → Logs (check for errors)
- **Vercel**: Dashboard → Analytics (check performance)

### Update CORS if Needed
If you add a custom domain, update in Render:
```
CORS_ORIGINS=https://your-frontend-name.vercel.app,https://www.your-domain.com
```

### Keep Dependencies Updated
```bash
# Backend
pip list --outdated

# Frontend
npm outdated
```

---

## 🎉 YOU'RE DONE!

Your application is now live:
- **Backend**: https://prism-api.onrender.com
- **Frontend**: https://your-frontend-name.vercel.app

Any changes you push to GitHub will automatically redeploy!

---

## 💡 TIPS

1. **Free Tier Limitations**:
   - Render free tier spins down after 15 minutes of inactivity
   - Upgrade to Standard for always-on service

2. **Custom Domain**:
   - Add in Vercel Settings → Domains
   - Update CORS_ORIGINS in Render

3. **Monitoring**:
   - Set up alerts in Render for service failures
   - Monitor Vercel analytics for performance

4. **Debugging**:
   - Always check logs first
   - Use browser DevTools (F12) for frontend issues
   - Test locally before deploying

---

## 🆘 NEED HELP?

1. Check DEPLOYMENT_ISSUES_SOLUTIONS.md for common problems
2. Check DEPLOYMENT_GUIDE.md for detailed instructions
3. Check service logs (Render/Vercel Dashboard)
4. Check browser console (F12)
