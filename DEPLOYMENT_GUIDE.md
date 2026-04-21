# Complete Deployment Guide: Vercel (Frontend) + Render (Backend)

## 📋 Pre-Deployment Checklist

### Backend (Render)
- [ ] All environment variables configured in Render dashboard
- [ ] MongoDB Atlas IP whitelist includes Render IPs
- [ ] Redis instance accessible from Render
- [ ] Neo4j Aura accessible from Render
- [ ] Pinecone API key valid
- [ ] SendGrid API key valid
- [ ] Groq API key valid

### Frontend (Vercel)
- [ ] Backend URL updated in environment variables
- [ ] Build command verified: `npm run build`
- [ ] Output directory set to: `dist`
- [ ] Node version set to 18.x

---

## 🚀 BACKEND DEPLOYMENT (Render)

### Step 1: Prepare Backend Repository

1. Ensure `requirements.txt` is up to date:
```bash
pip freeze > requirements.txt
```

2. Verify `Procfile` exists with correct commands

3. Verify `runtime.txt` specifies Python 3.11.7

4. Check `.env.production` template is in place

### Step 2: Create Render Web Service

1. Go to [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `prism-api`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 4 --timeout 120`
   - **Instance Type**: Standard (minimum for production)

### Step 3: Set Environment Variables in Render Dashboard

Go to your service → Environment → Add the following:

```
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend-name.vercel.app
GROQ_API_KEY=<your-groq-key>
OPENAI_API_KEY=<your-openai-key>
REDIS_URL=<your-redis-url>
PINECONE_API_KEY=<your-pinecone-key>
MONGO_URI=<your-mongodb-uri>
NEO4J_URI=<your-neo4j-uri>
NEO4J_USER=<your-neo4j-user>
NEO4J_PASSWORD=<your-neo4j-password>
NEO4J_DATABASE=<your-neo4j-database>
SENDGRID_API_KEY=<your-sendgrid-key>
SENDER_EMAIL=<your-sender-email>
YOUTUBE_API_KEY=<your-youtube-key>
JWT_SECRET=<your-jwt-secret>
ENCRYPTION_KEY=<your-encryption-key>
CELERY_BROKER_URL=<your-redis-url>
CELERY_RESULT_BACKEND=<your-redis-url>
```

### Step 4: Create Celery Worker Service (Optional but Recommended)

1. Click "New +" → "Background Worker"
2. Select same repository
3. Configure:
   - **Name**: `prism-celery-worker`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `celery -A app.core.celery_app worker --loglevel=info --queues=email,default --concurrency=4`
4. Add same environment variables as Web Service

### Step 5: Verify Backend Deployment

Once deployed, test the health endpoint:
```bash
curl https://prism-api.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## 🎨 FRONTEND DEPLOYMENT (Vercel)

### Step 1: Prepare Frontend Repository

1. Ensure `package.json` build script is correct:
```json
"build": "vite build"
```

2. Verify `vite.config.ts` is configured properly

3. Create `.env.production` with backend URL:
```
VITE_API_URL=https://prism-api.onrender.com
```

### Step 2: Deploy to Vercel

#### Option A: Using Vercel CLI
```bash
cd Frontend
npm install -g vercel
vercel --prod
```

#### Option B: Using Vercel Dashboard
1. Go to [vercel.com](https://vercel.com)
2. Click "Add New..." → "Project"
3. Import your GitHub repository
4. Configure:
   - **Framework**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### Step 3: Set Environment Variables in Vercel

1. Go to Project Settings → Environment Variables
2. Add:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://prism-api.onrender.com`
   - **Environments**: Production, Preview, Development

### Step 4: Configure Custom Domain (Optional)

1. Go to Project Settings → Domains
2. Add your custom domain
3. Update DNS records as instructed by Vercel

### Step 5: Verify Frontend Deployment

1. Visit your Vercel deployment URL
2. Check browser console for any API errors
3. Test API connectivity by making a request to `/health`

---

## 🔗 CONNECTING FRONTEND TO BACKEND

### Update CORS in Backend

In Render dashboard, update `CORS_ORIGINS`:
```
https://your-frontend-name.vercel.app,https://www.your-domain.com
```

### Update API URL in Frontend

In Vercel dashboard, update `VITE_API_URL`:
```
https://prism-api.onrender.com
```

---

## 🐛 TROUBLESHOOTING

### Backend Issues

#### 1. Service Won't Start
- Check logs: Render Dashboard → Logs
- Verify all environment variables are set
- Check Python version compatibility
- Ensure `requirements.txt` has all dependencies

#### 2. Database Connection Errors
- Verify MongoDB Atlas IP whitelist includes Render IPs
- Check Redis connection string format
- Verify Neo4j credentials
- Test connections locally first

#### 3. CORS Errors
- Verify `CORS_ORIGINS` includes frontend URL
- Check frontend is using correct backend URL
- Clear browser cache and cookies

#### 4. Timeout Errors
- Increase `STARTUP_TIMEOUT_SECONDS` in environment
- Check database connection timeouts
- Verify network connectivity to external services

### Frontend Issues

#### 1. Build Fails
```bash
# Clear cache and rebuild
rm -rf node_modules dist
npm install
npm run build
```

#### 2. API Calls Fail
- Check `VITE_API_URL` is correct
- Verify backend is running
- Check browser console for CORS errors
- Verify network tab shows correct API endpoint

#### 3. Blank Page
- Check browser console for JavaScript errors
- Verify all environment variables are loaded
- Check Vercel build logs for errors

---

## 📊 MONITORING & MAINTENANCE

### Backend Monitoring
- Render Dashboard → Metrics
- Check CPU, Memory, Network usage
- Monitor error logs regularly
- Set up alerts for service failures

### Frontend Monitoring
- Vercel Dashboard → Analytics
- Monitor build times and deployment status
- Check error tracking (if configured)
- Monitor Core Web Vitals

### Health Checks
```bash
# Backend health
curl https://prism-api.onrender.com/health

# Backend performance stats
curl https://prism-api.onrender.com/performance-stats

# Celery health (if worker deployed)
curl https://prism-api.onrender.com/celery-health
```

---

## 🔄 DEPLOYMENT WORKFLOW

### For Backend Updates
1. Push changes to GitHub
2. Render automatically redeploys
3. Monitor deployment in Render Dashboard
4. Verify health endpoint
5. Check logs for errors

### For Frontend Updates
1. Push changes to GitHub
2. Vercel automatically builds and deploys
3. Monitor build in Vercel Dashboard
4. Test in preview environment first
5. Promote to production when ready

---

## 🔐 SECURITY BEST PRACTICES

1. **Never commit `.env` files** - Use `.env.example` instead
2. **Rotate secrets regularly** - Update API keys periodically
3. **Use HTTPS only** - Both Vercel and Render provide SSL
4. **Enable CORS properly** - Only allow trusted origins
5. **Monitor logs** - Check for suspicious activity
6. **Keep dependencies updated** - Run `npm audit` and `pip audit`

---

## 📞 SUPPORT

- **Render Docs**: https://render.com/docs
- **Vercel Docs**: https://vercel.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Vite Docs**: https://vitejs.dev

---

## ✅ FINAL CHECKLIST

- [ ] Backend deployed on Render
- [ ] Frontend deployed on Vercel
- [ ] Environment variables configured
- [ ] CORS properly configured
- [ ] Health endpoints responding
- [ ] API calls working from frontend
- [ ] Database connections stable
- [ ] Monitoring set up
- [ ] Backups configured
- [ ] Domain configured (if applicable)
