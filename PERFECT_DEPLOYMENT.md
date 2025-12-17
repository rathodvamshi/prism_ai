# 🚀 PERFECT DEPLOYMENT GUIDE

## 📋 PRE-DEPLOYMENT CHECKLIST

### ✅ 1. Environment Variables Setup (CRITICAL)
Set these in your Render dashboard **BEFORE** deployment:

```bash
# Database & Cache (REQUIRED)
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/prism
CELERY_BROKER_URL=rediss://user:pass@redis-host:port
CELERY_RESULT_BACKEND=rediss://user:pass@redis-host:port

# Email Service (REQUIRED)  
SENDGRID_API_KEY=SG.xxxxx
SENDER_EMAIL=noreply@yourdomain.com

# AI Services (REQUIRED)
GROQ_API_KEY=gsk_xxxxx
PINECONE_API_KEY=xxxxx
PINECONE_INDEX_NAME=prism-memory
PINECONE_ENVIRONMENT=us-east-1

# Graph Database (OPTIONAL)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=xxxxx
```

### ✅ 2. Render Service Configuration

**Backend API Service:**
- **Service Type**: Web Service
- **Repository**: Your GitHub repo
- **Root Directory**: `prism-backend`
- **Runtime**: Python 3
- **Build Command**: 
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout-keep-alive 65
  ```
- **Health Check Path**: `/health`

**Celery Worker Service:**
- **Service Type**: Background Worker  
- **Repository**: Same GitHub repo
- **Root Directory**: `prism-backend`
- **Runtime**: Python 3
- **Build Command**: Same as API
- **Start Command**:
  ```bash
  celery -A app.core.celery_app worker --loglevel=info --queues=email,default --concurrency=2
  ```

### ✅ 3. Vercel Frontend Configuration

**Frontend Service:**
- **Framework**: Vite (Auto-detected)
- **Root Directory**: `./` (Project root)
- **Build Command**: `cd Frontend && npm install && npm run build`
- **Output Directory**: `Frontend/dist`
- **Environment Variables**:
  ```bash
  VITE_API_BASE_URL=https://your-backend-api.onrender.com
  ```

## 🔧 DEPLOYMENT STEPS

### Step 1: Update Git Repository
```bash
git add .
git commit -m "Configure perfect deployment setup"
git push origin main
```

### Step 2: Deploy Backend on Render
1. Go to Render Dashboard
2. New → Web Service
3. Connect your GitHub repo
4. Configure as per checklist above
5. Add all environment variables
6. Deploy

### Step 3: Deploy Worker on Render  
1. New → Background Worker
2. Same repo, same configuration
3. Same environment variables
4. Deploy

### Step 4: Deploy Frontend on Vercel
1. Import project from GitHub
2. Set `VITE_API_BASE_URL` to your Render API URL
3. Deploy

## 🐛 TROUBLESHOOTING

### Backend Issues:
- **"uvicorn: command not found"**: Wrong service type, use Web Service not Static Site
- **"No module named app"**: Wrong Root Directory, should be `prism-backend`  
- **"Connection failed"**: Check environment variables, especially MONGO_URI and CELERY_BROKER_URL

### Worker Issues:
- **"Broker connection failed"**: CELERY_BROKER_URL must match API service
- **"No active workers"**: Worker service not started or crashed

### Frontend Issues:
- **"API calls failing"**: Check VITE_API_BASE_URL points to correct Render URL
- **"Build failed"**: Ensure vercel.json is in project root, not Frontend folder

## 🎯 SUCCESS VALIDATION

### Test API Health:
```bash
curl https://your-api.onrender.com/health
# Should return: {"status": "healthy", "timestamp": "..."}
```

### Test Worker Health:
```bash  
curl https://your-api.onrender.com/health/celery
# Should return: {"celery": "ok", "redis": "connected"}
```

### Test Frontend:
- Visit your Vercel URL
- Check browser console for API connection errors
- Test login/signup functionality

## 🏆 PERFECT DEPLOYMENT ACHIEVED!

When all services show:
- ✅ API: "Service is live" (Green status)
- ✅ Worker: "Running" (Green status)  
- ✅ Frontend: "Deployed" (Green status)

Your PRISM AI Studio is perfectly deployed! 🎉