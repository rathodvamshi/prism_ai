# 🔧 RENDER MANUAL SETUP GUIDE

## 🚀 STEP-BY-STEP RENDER CONFIGURATION

### **Service 1: Backend API**

1. **Go to Render Dashboard** → New → Web Service
2. **Connect Repository**: Select your GitHub repo
3. **Service Configuration**:
   ```
   Name: prism-backend-api
   Environment: Python 3
   Region: Oregon (US West) or Frankfurt (EU)
   Branch: main
   Root Directory: prism-backend
   ```

4. **Build & Deploy Settings**:
   ```
   Build Command: pip install -r requirements.txt
   Start Command: python -m gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT
   ```

5. **Advanced Settings**:
   ```
   Auto-Deploy: Yes
   Health Check Path: /health
   ```

### **Service 2: Celery Worker**

1. **New** → Background Worker
2. **Same Repository** as API service
3. **Service Configuration**:
   ```
   Name: prism-celery-worker
   Environment: Python 3
   Region: Same as API
   Branch: main
   Root Directory: prism-backend
   ```

4. **Build & Deploy Settings**:
   ```
   Build Command: pip install -r requirements.txt
   Start Command: python -m celery -A app.core.celery_app worker --loglevel=info --queues=email,default --concurrency=1
   ```

## 🔑 ENVIRONMENT VARIABLES (Both Services)

Add these in **Environment** tab of BOTH services:

```
CELERY_BROKER_URL=rediss://default:your_password@your_redis_host:6379
CELERY_RESULT_BACKEND=rediss://default:your_password@your_redis_host:6379
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/prism
SENDGRID_API_KEY=SG.your_sendgrid_key
SENDER_EMAIL=noreply@yourdomain.com
GROQ_API_KEY=gsk_your_groq_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=prism-memory
PINECONE_ENVIRONMENT=us-east-1
NEO4J_URI=neo4j+s://your_neo4j_host
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

## 🎯 ALTERNATIVE: Use Blueprint (If Above Fails)

If manual setup is blocked, use the render.yaml file:

1. **New** → Blueprint
2. **Repository**: Connect your GitHub repo
3. **Blueprint File**: `render.yaml` (auto-detected)
4. **Deploy**

## ✅ VERIFICATION

After deployment:
- API Health: `https://your-api-url.onrender.com/health`
- Should return: `{"status":"healthy"}`