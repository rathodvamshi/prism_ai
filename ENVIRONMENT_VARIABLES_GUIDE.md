# 🔐 Environment Variables Complete Guide

## Backend Environment Variables (Render)

### Required Variables

#### Server Configuration
```
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8000
```

#### CORS Configuration
```
# Update with your Vercel frontend URL
CORS_ORIGINS=https://your-frontend-name.vercel.app,https://www.your-domain.com
```

#### AI/LLM Services
```
# Get from: https://console.groq.com/keys
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx

# Optional - Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxx
```

#### Database Services

**Redis** (Get from Redis Labs or similar)
```
# Format: rediss://user:password@host:port (note: rediss with 's' for SSL)
REDIS_URL=rediss://default:xxxxxxxxxxxxx@redis-xxxxx.c16.us-east-1-2.ec2.cloud.redislabs.com:xxxxx
REDIS_SOCKET_KEEPALIVE=true
REDIS_SOCKET_KEEPALIVE_INTERVAL=30
REDIS_RETRY_ON_TIMEOUT=true
REDIS_MAX_RETRIES=3
REDIS_SSL=true
REDIS_SSL_CERT_REQS=none
```

**MongoDB Atlas** (Get from MongoDB Atlas)
```
# Format: mongodb+srv://username:password@cluster.mongodb.net/database
MONGO_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/prismdb?retryWrites=true&w=majority
```

**Neo4j Aura** (Get from Neo4j Aura)
```
# Format: neo4j+s://instance-id.databases.neo4j.io:7687
NEO4J_URI=neo4j+s://xxxxxxxxxxxxx.databases.neo4j.io:7687
NEO4J_USER=xxxxxxxxxxxxx
NEO4J_PASSWORD=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NEO4J_DATABASE=neo4j
NEO4J_ENCRYPTED=true
NEO4J_MAX_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT=30
NEO4J_TRUST=TRUST_ALL_CERTIFICATES
NEO4J_RETRY_ATTEMPTS=3
NEO4J_RETRY_DELAY=1
```

**Pinecone** (Get from Pinecone)
```
# Get from: https://app.pinecone.io/
PINECONE_API_KEY=pcsk_xxxxxxxxxxxxxxxxxxxxx
PINECONE_TIMEOUT=30
```

#### Email Service
```
# Get from: https://sendgrid.com/
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
SENDER_EMAIL=your-email@example.com
```

#### Media Services
```
# Get from: https://console.cloud.google.com/
YOUTUBE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxx
MEDIA_DEFAULT_MODE=redirect
MEDIA_CACHE_TTL=172800
MEDIA_USE_SCRAPER_FALLBACK=true
```

#### Security
```
# Generate random string for JWT
JWT_SECRET=your-random-secret-string-here

# Generate base64 encoded key for encryption
# Python: import base64; print(base64.b64encode(os.urandom(32)).decode())
ENCRYPTION_KEY=5Q_PSus1BJ80iJtiLS6ZhjhFHY2vmjPWJHv8lm-41oU=
```

#### Celery Configuration
```
# Same as REDIS_URL
CELERY_BROKER_URL=rediss://default:xxxxxxxxxxxxx@redis-xxxxx.c16.us-east-1-2.ec2.cloud.redislabs.com:xxxxx
CELERY_RESULT_BACKEND=rediss://default:xxxxxxxxxxxxx@redis-xxxxx.c16.us-east-1-2.ec2.cloud.redislabs.com:xxxxx
```

#### Connection Monitoring
```
ENABLE_CONNECTION_MONITORING=true
CONNECTION_HEALTH_CHECK_INTERVAL=60
CONNECTION_RETRY_BACKOFF=exponential
LOG_CONNECTION_EVENTS=false
```

#### Service Timeouts (milliseconds)
```
REDIS_TIMEOUT_MS=500
MONGODB_TIMEOUT_MS=5000
NEO4J_TIMEOUT_MS=15000
PINECONE_TIMEOUT_MS=8000
```

#### Startup Configuration
```
STARTUP_TIMEOUT_SECONDS=30
DEFER_DB_VALIDATION=true
ENABLE_GRACEFUL_DEGRADATION=true
```

---

## Frontend Environment Variables (Vercel)

### Required Variables

#### API Configuration
```
# Update with your Render backend URL
VITE_API_URL=https://prism-api.onrender.com
```

#### Environment
```
VITE_ENV=production
```

---

## 🔑 How to Get Each API Key

### 1. Groq API Key
```
1. Go to https://console.groq.com/keys
2. Sign up or log in
3. Create new API key
4. Copy and paste into GROQ_API_KEY
```

### 2. MongoDB Atlas Connection String
```
1. Go to https://www.mongodb.com/cloud/atlas
2. Create cluster
3. Click "Connect"
4. Choose "Drivers"
5. Copy connection string
6. Replace <username> and <password>
7. Paste into MONGO_URI
```

### 3. Redis URL
```
1. Go to https://redis.com/try-free/
2. Create free database
3. Copy connection string
4. Format: rediss://user:password@host:port
5. Paste into REDIS_URL
```

### 4. Neo4j Aura Connection
```
1. Go to https://neo4j.com/cloud/aura/
2. Create instance
3. Copy connection details
4. Paste into NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
```

### 5. Pinecone API Key
```
1. Go to https://app.pinecone.io/
2. Sign up or log in
3. Create API key
4. Copy and paste into PINECONE_API_KEY
```

### 6. SendGrid API Key
```
1. Go to https://sendgrid.com/
2. Sign up or log in
3. Go to Settings → API Keys
4. Create new API key
5. Copy and paste into SENDGRID_API_KEY
```

### 7. YouTube API Key
```
1. Go to https://console.cloud.google.com/
2. Create new project
3. Enable YouTube Data API v3
4. Create API key
5. Copy and paste into YOUTUBE_API_KEY
```

### 8. JWT Secret
```
# Generate random string (any random string works)
# Examples:
- your-super-secret-key-12345
- random-jwt-secret-xyz789
- any-random-string-you-want
```

### 9. Encryption Key
```
# Generate base64 encoded key
# Python:
import base64
import os
key = base64.b64encode(os.urandom(32)).decode()
print(key)

# Or use online generator:
# https://www.base64encode.org/
```

---

## 📋 Render Dashboard Setup

### Step 1: Create Web Service
1. Go to render.com → Dashboard
2. Click "New +" → "Web Service"
3. Select your GitHub repository
4. Fill in basic info

### Step 2: Add Environment Variables
1. Go to Service Settings → Environment Variables
2. Click "Add Environment Variable"
3. For each variable:
   - **Key**: Variable name (e.g., `GROQ_API_KEY`)
   - **Value**: Paste the value
   - Click "Add"

### Step 3: Verify All Variables
```
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend-name.vercel.app
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
REDIS_URL=rediss://default:xxxxxxxxxxxxx@...
MONGO_URI=mongodb+srv://username:password@...
NEO4J_URI=neo4j+s://xxxxxxxxxxxxx@...
NEO4J_USER=xxxxxxxxxxxxx
NEO4J_PASSWORD=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NEO4J_DATABASE=neo4j
PINECONE_API_KEY=pcsk_xxxxxxxxxxxxxxxxxxxxx
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
SENDER_EMAIL=your-email@example.com
YOUTUBE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxx
JWT_SECRET=your-random-secret-string-here
ENCRYPTION_KEY=5Q_PSus1BJ80iJtiLS6ZhjhFHY2vmjPWJHv8lm-41oU=
CELERY_BROKER_URL=rediss://default:xxxxxxxxxxxxx@...
CELERY_RESULT_BACKEND=rediss://default:xxxxxxxxxxxxx@...
ENABLE_CONNECTION_MONITORING=true
CONNECTION_HEALTH_CHECK_INTERVAL=60
CONNECTION_RETRY_BACKOFF=exponential
LOG_CONNECTION_EVENTS=false
REDIS_TIMEOUT_MS=500
MONGODB_TIMEOUT_MS=5000
NEO4J_TIMEOUT_MS=15000
PINECONE_TIMEOUT_MS=8000
STARTUP_TIMEOUT_SECONDS=30
DEFER_DB_VALIDATION=true
ENABLE_GRACEFUL_DEGRADATION=true
```

---

## 📋 Vercel Dashboard Setup

### Step 1: Create Project
1. Go to vercel.com → Dashboard
2. Click "Add New..." → "Project"
3. Select your GitHub repository
4. Select "Frontend" folder as root

### Step 2: Add Environment Variables
1. Go to Project Settings → Environment Variables
2. Click "Add New"
3. For each variable:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://prism-api.onrender.com`
   - **Environments**: Select all (Production, Preview, Development)
   - Click "Add"

### Step 3: Redeploy
1. Go to Deployments
2. Click "Redeploy" on latest deployment
3. Wait for build to complete

---

## ✅ Verification

### Backend Variables
```bash
# Test each variable is accessible
curl https://prism-api.onrender.com/health
# Should return: {"status": "healthy", ...}
```

### Frontend Variables
```bash
# Check in browser console
console.log(import.meta.env.VITE_API_URL)
# Should print: https://prism-api.onrender.com
```

---

## 🔒 Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` instead
2. **Rotate secrets regularly** - Update API keys every 3-6 months
3. **Use strong JWT secret** - At least 32 characters
4. **Keep encryption key safe** - Don't share with anyone
5. **Monitor API key usage** - Check for unusual activity
6. **Use environment-specific keys** - Different keys for dev/prod
7. **Revoke old keys** - Delete unused API keys
8. **Use HTTPS only** - Both Vercel and Render provide SSL

---

## 🆘 Troubleshooting

### Variable Not Loading
```
1. Check spelling (case-sensitive)
2. Verify in Render/Vercel dashboard
3. Redeploy after adding variable
4. Check logs for error messages
```

### API Key Invalid
```
1. Verify key is correct
2. Check key hasn't expired
3. Verify key has correct permissions
4. Generate new key if needed
```

### Connection Timeout
```
1. Verify connection string format
2. Check IP whitelist (MongoDB, etc.)
3. Verify credentials are correct
4. Test connection locally first
```

---

## 📞 Support

- **Render Docs**: https://render.com/docs
- **Vercel Docs**: https://vercel.com/docs
- **Environment Variables**: https://12factor.net/config
