# ☁️ Cloud-Native Deployment Guide

## Overview
PRISM is a full-stack application with separate deployment strategies:

### Frontend (React/Vite) → Vercel
- ✅ Static site generation with Vite
- ✅ Optimized asset caching
- ✅ Global CDN distribution

### Backend (FastAPI/Python) → Render
- ✅ SSL Redis connections (rediss://)
- ✅ IST → UTC timezone conversion
- ✅ Celery for reliable background tasks
- ✅ No localhost dependencies

## Prerequisites

### Required Environment Variables

```bash
# Redis (Cloud - Use rediss:// with SSL)
CELERY_BROKER_URL=rediss://default:password@redis-host:port
CELERY_RESULT_BACKEND=rediss://default:password@redis-host:port
# OR fallback to REDIS_URL
REDIS_URL=rediss://default:password@redis-host:port

# MongoDB (Cloud)
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/prism

# SendGrid
SENDGRID_API_KEY=SG.xxx
SENDER_EMAIL=noreply@yourdomain.com

# AI Services
GROQ_API_KEY=xxx
PINECONE_API_KEY=xxx
PINECONE_INDEX_NAME=prism-memory
PINECONE_INDEX_TYPE=serverless  # "serverless" (cloud-native) or "pod" (legacy)
PINECONE_ENVIRONMENT=us-east-1  # AWS region for serverless, or "gcp-starter" for pod-based

# Neo4j (Cloud)
NEO4J_URI=neo4j+s://cluster.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=xxx
```

## Frontend Deployment on Vercel

### Monorepo Configuration
The project uses a monorepo structure with Frontend and Backend in separate directories. Vercel is configured to deploy only the Frontend.

**Required Files (Already Created):**
- `vercel.json` - Root-level Vercel configuration
- `package.json` - Root-level package with build scripts  
- `.vercelignore` - Excludes Python backend files

**Vercel Settings:**
- **Root Directory**: `./` (project root)
- **Build Command**: `cd Frontend && npm install && npm run build`
- **Output Directory**: `Frontend/dist`
- **Install Command**: `cd Frontend && npm install`

### Environment Variables for Frontend
```bash
# API Base URL (point to your Render backend)
VITE_API_BASE_URL=https://your-backend-api.onrender.com
VITE_APP_NAME=PRISM AI Studio
```

## Backend Deployment on Render

### Step 1: Create Web Service (API)

1. **New → Web Service**
2. **Root Directory**: `prism-backend` (Backend only)
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
5. **Environment Variables**: Add all required vars (see above)
6. **Health Check Path**: `/health`

### Step 2: Create Background Worker (Celery)

1. **New → Background Worker**
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `celery -A app.core.celery_app worker --loglevel=info --queues=email,default --concurrency=4`
4. **Environment Variables**: Same as Web Service (especially `CELERY_BROKER_URL`)

### Step 3: Configure Redis (Upstash/Render Redis)

1. Create Redis instance (Upstash or Render Redis)
2. Copy connection string (should be `rediss://...`)
3. Set `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` in both services

## Deployment Checklist

- [ ] **Config**: `config.py` reads `CELERY_BROKER_URL` from environment
- [ ] **SSL**: `celery_app.py` has `broker_use_ssl` and `redis_backend_use_ssl` configured
- [ ] **Time**: `tasks.py` converts IST input to UTC datetime object before `apply_async`
- [ ] **Render**: Two separate services defined (Web Service + Background Worker)
- [ ] **Cleanup**: Old `email_worker.py` references removed from `main.py`
- [ ] **Redis**: Using `rediss://` (SSL) for cloud Redis connections
- [ ] **MongoDB**: Using `mongodb+srv://` for cloud MongoDB
- [ ] **Timezone**: All datetime operations use timezone-aware objects (UTC for Celery)

## Testing Cloud Deployment

### 1. Test Task Creation
```bash
curl -X POST https://your-api.onrender.com/tasks/confirm \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "description": "Test reminder",
    "due_date": "2025-12-17 21:00:00"
  }'
```

### 2. Check Celery Worker Logs
```bash
# In Render dashboard, check Background Worker logs
# Should see: "👷 [Cloud Worker] Waking up for Task..."
```

### 3. Verify Email Sent
- Check SendGrid dashboard for sent emails
- Verify task status updated to "completed" in MongoDB

## Troubleshooting

### "Broker Not Found"
- ✅ Check: `CELERY_BROKER_URL` uses `rediss://` (with SSL)
- ✅ Check: `broker_use_ssl` is set in `celery_app.py`
- ✅ Check: Both API and Worker use the same Redis URL

### "Task Not Received"
- ✅ Check: API and Worker connected to same `CELERY_BROKER_URL`
- ✅ Check: Worker is listening to `email` and `default` queues
- ✅ Check: Redis connection is working (test with `redis-cli`)

### "Email Sent at Wrong Time"
- ✅ Check: `eta` parameter receives UTC datetime object (not naive, not IST)
- ✅ Check: IST → UTC conversion in `tasks.py` is correct
- ✅ Check: Celery worker timezone is set to `Asia/Kolkata` in config

### "Worker Crashing on Startup"
- ✅ Check: No circular imports (don't import `main.py` in `celery_app.py`)
- ✅ Check: All dependencies installed (`pip install -r requirements.txt`)
- ✅ Check: MongoDB connection string is valid

## Production Best Practices

1. **Separate Services**: Always run API and Celery worker as separate services
2. **SSL Redis**: Always use `rediss://` for production Redis
3. **Environment Variables**: Never hardcode credentials
4. **Health Checks**: Configure health check endpoints
5. **Logging**: Monitor both API and Worker logs
6. **Scaling**: Scale Celery workers independently based on queue length

## Monitoring

### Check Celery Status
```bash
celery -A app.core.celery_app inspect active
celery -A app.core.celery_app inspect scheduled
celery -A app.core.celery_app inspect stats
```

### Check Redis Connection
```bash
redis-cli -u $CELERY_BROKER_URL ping
```

## Architecture

```
User → API (Render Web Service)
  ↓
MongoDB (Save Task)
  ↓
Celery (Schedule with eta=UTC)
  ↓
Redis Queue (rediss://)
  ↓
Worker (Render Background Worker)
  ↓
SendGrid (Send Email)
  ↓
MongoDB (Update Status)
```
