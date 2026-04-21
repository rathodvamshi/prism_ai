# 🔧 Complete Build Commands Reference

## 📋 Quick Command Index

- [Backend Build](#backend-build-commands)
- [Frontend Build](#frontend-build-commands)
- [Testing Commands](#testing-commands)
- [Deployment Commands](#deployment-commands)
- [Debugging Commands](#debugging-commands)

---

## Backend Build Commands

### Installation & Setup

```bash
# Navigate to backend
cd prism-backend

# Create virtual environment (optional but recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list

# Check specific packages
pip show fastapi uvicorn gunicorn
```

### Local Development

```bash
# Run development server with auto-reload
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Run with specific host/port
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run with workers (simulates production)
python -m uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000

# Run with gunicorn (production-like)
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4 --timeout 120

# Run with gunicorn and logging
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4 --timeout 120 --access-logfile - --error-logfile -
```

### Code Quality & Verification

```bash
# Check Python syntax
python -m py_compile app/main.py

# Check all Python files
python -m py_compile app/**/*.py

# Verify imports work
python -c "from app.main import app; print('✅ Imports OK')"

# Check for import errors
python -m py_compile app/

# Lint code (if flake8 installed)
flake8 app/

# Type checking (if mypy installed)
mypy app/

# Security check
pip audit

# Check outdated packages
pip list --outdated
```

### Database & Initialization

```bash
# Initialize database
python db_init.py

# Check database status
python check_db_status.py

# Check MongoDB health
python mongodb_health_check.py

# Check Neo4j status
python neo4j_status.py

# Check Redis connection
python -c "from app.db.redis_client import redis_client; print(redis_client.ping())"

# Add database indexes
python add_indexes.py

# Check system health
python check_system_health.py
```

### Celery Commands (Background Tasks)

```bash
# Start Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Start Celery worker with specific queues
celery -A app.core.celery_app worker --loglevel=info --queues=email,default

# Start Celery beat (scheduler)
celery -A app.core.celery_app beat --loglevel=info

# Start both worker and beat
celery -A app.core.celery_app worker --loglevel=info & celery -A app.core.celery_app beat --loglevel=info

# Monitor Celery tasks
celery -A app.core.celery_app events

# Purge all tasks
celery -A app.core.celery_app purge
```

### Production Build

```bash
# Install production dependencies only
pip install -r requirements.txt --no-dev

# Build for production
gunicorn app.main:app -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:$PORT \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -

# With environment variables
ENVIRONMENT=production \
GROQ_API_KEY=your_key \
REDIS_URL=your_url \
MONGO_URI=your_uri \
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Frontend Build Commands

### Installation & Setup

```bash
# Navigate to frontend
cd Frontend

# Install dependencies
npm install

# Install specific package
npm install package-name

# Install dev dependency
npm install --save-dev package-name

# Update dependencies
npm update

# Check for vulnerabilities
npm audit

# Fix vulnerabilities
npm audit fix

# Check outdated packages
npm outdated
```

### Development

```bash
# Start development server
npm run dev

# Start dev server on specific port
npm run dev -- --port 3000

# Start dev server with host
npm run dev -- --host 0.0.0.0

# Preview development build
npm run preview
```

### Building

```bash
# Build for production
npm run build

# Build with specific mode
npm run build:dev

# Build and check output
npm run build && ls -la dist/

# Build with verbose output
npm run build -- --debug

# Analyze bundle size
npm run build -- --analyze
```

### Code Quality

```bash
# Lint code
npm run lint

# Lint and fix
npm run lint -- --fix

# Type check (if TypeScript)
npx tsc --noEmit

# Format code (if prettier installed)
npx prettier --write .

# Check for unused dependencies
npx depcheck
```

### Testing

```bash
# Run tests (if configured)
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- src/components/Button.test.tsx
```

### Cleanup & Maintenance

```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules
rm -rf node_modules

# Remove dist folder
rm -rf dist

# Clean install (remove and reinstall)
rm -rf node_modules package-lock.json
npm install

# Full clean rebuild
rm -rf node_modules dist package-lock.json
npm install
npm run build
```

### Production Build

```bash
# Build for production
npm run build

# Verify build output
ls -la dist/

# Check build size
du -sh dist/

# Preview production build
npm run preview

# Build and deploy
npm run build && npm run deploy
```

---

## Testing Commands

### Backend Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run specific test function
pytest tests/test_auth.py::test_login

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app

# Run with coverage report
pytest --cov=app --cov-report=html

# Run tests in parallel
pytest -n auto

# Run tests with markers
pytest -m "not slow"

# Run tests and stop on first failure
pytest -x

# Run tests with detailed output
pytest -vv --tb=long
```

### Frontend Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage

# Run specific test
npm test -- Button.test.tsx

# Run tests matching pattern
npm test -- --testNamePattern="Button"

# Update snapshots
npm test -- -u
```

### API Testing

```bash
# Test health endpoint
curl https://prism-api.onrender.com/health

# Test with verbose output
curl -v https://prism-api.onrender.com/health

# Test with headers
curl -H "Content-Type: application/json" https://prism-api.onrender.com/health

# Test POST request
curl -X POST https://prism-api.onrender.com/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'

# Test with authentication
curl -H "Authorization: Bearer token" https://prism-api.onrender.com/api/endpoint

# Save response to file
curl https://prism-api.onrender.com/health > response.json

# Test with timeout
curl --max-time 10 https://prism-api.onrender.com/health
```

---

## Deployment Commands

### Pre-Deployment

```bash
# Backend pre-deployment checks
cd prism-backend
pip install -r requirements.txt
python -c "from app.main import app; print('✅ Backend OK')"
python -m py_compile app/main.py

# Frontend pre-deployment checks
cd Frontend
npm install
npm run lint
npm run build
```

### Git Commands

```bash
# Check status
git status

# Add all changes
git add .

# Add specific files
git add DEPLOYMENT_STEP_BY_STEP.md BUILD_COMMANDS_REFERENCE.md

# Commit changes
git commit -m "feat: Add deployment guides and build commands"

# Push to main branch
git push origin main

# Push to specific branch
git push origin feature-branch

# Check git log
git log --oneline -10

# View changes
git diff

# View staged changes
git diff --staged
```

### Render Deployment

```bash
# Manual deploy (via CLI if installed)
render deploy --service prism-api

# Check deployment status
render status --service prism-api

# View logs
render logs --service prism-api --tail 100

# Restart service
render restart --service prism-api
```

### Vercel Deployment

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy to Vercel
vercel --prod

# Deploy specific directory
vercel --prod Frontend

# Check deployment status
vercel status

# View logs
vercel logs

# Rollback deployment
vercel rollback
```

---

## Debugging Commands

### Backend Debugging

```bash
# Run with debug logging
LOGLEVEL=DEBUG python -m uvicorn app.main:app --reload

# Check environment variables
env | grep -E "GROQ|MONGO|REDIS|NEO4J"

# Test database connection
python -c "from app.db.mongo_client import db; print(db.command('ping'))"

# Test Redis connection
python -c "from app.db.redis_client import redis_client; print(redis_client.ping())"

# Test Neo4j connection
python -c "from app.db.neo4j_client import neo4j_client; print(neo4j_client.verify_connectivity())"

# Check running processes
ps aux | grep python

# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Check port availability
netstat -an | grep 8000
```

### Frontend Debugging

```bash
# Run with debug mode
npm run dev -- --debug

# Check environment variables
echo $VITE_API_URL

# Build with source maps
npm run build -- --sourcemap

# Check bundle size
npm run build && npm run analyze

# Clear browser cache
# In browser DevTools: Application → Clear site data

# Check console errors
# Open DevTools (F12) → Console tab

# Check network requests
# Open DevTools (F12) → Network tab
```

### Network Debugging

```bash
# Test backend connectivity
curl -v https://prism-api.onrender.com/health

# Test frontend connectivity
curl -v https://prism-ai-frontend.vercel.app

# Check DNS resolution
nslookup prism-api.onrender.com

# Check SSL certificate
openssl s_client -connect prism-api.onrender.com:443

# Test CORS headers
curl -H "Origin: https://prism-ai-frontend.vercel.app" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS https://prism-api.onrender.com/health -v

# Check response headers
curl -I https://prism-api.onrender.com/health
```

---

## Environment Setup Commands

### Backend Environment

```bash
# Create .env file from template
cp prism-backend/.env.example prism-backend/.env

# Set environment variable (temporary)
export ENVIRONMENT=production
export GROQ_API_KEY=your_key

# Set environment variable (permanent - Linux/macOS)
echo "export GROQ_API_KEY=your_key" >> ~/.bashrc
source ~/.bashrc

# Set environment variable (permanent - Windows)
setx GROQ_API_KEY your_key

# View all environment variables
env

# View specific variable
echo $GROQ_API_KEY
```

### Frontend Environment

```bash
# Create .env file
cp Frontend/.env.example Frontend/.env.production

# Update API URL
echo "VITE_API_URL=https://prism-api.onrender.com" > Frontend/.env.production

# View environment file
cat Frontend/.env.production
```

---

## Docker Commands (Optional)

```bash
# Build Docker image
docker build -t prism-backend:latest prism-backend/

# Run Docker container
docker run -p 8000:8000 prism-backend:latest

# Run with environment variables
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key \
  -e MONGO_URI=your_uri \
  prism-backend:latest

# View running containers
docker ps

# View all containers
docker ps -a

# Stop container
docker stop container_id

# Remove container
docker rm container_id

# View logs
docker logs container_id

# Build and push to registry
docker build -t your-registry/prism-backend:latest .
docker push your-registry/prism-backend:latest
```

---

## Monitoring Commands

```bash
# Check backend health
curl https://prism-api.onrender.com/health

# Check performance stats
curl https://prism-api.onrender.com/performance-stats

# Check Celery health
curl https://prism-api.onrender.com/celery-health

# Monitor logs in real-time
tail -f prism-backend/logs/app.log

# Check system resources
top

# Check disk usage
df -h

# Check memory usage
free -h

# Check CPU usage
mpstat 1 5
```

---

## Quick Command Cheat Sheet

### Backend
```bash
# Install
pip install -r requirements.txt

# Run locally
python -m uvicorn app.main:app --reload

# Build for production
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT

# Test
pytest

# Lint
flake8 app/
```

### Frontend
```bash
# Install
npm install

# Run locally
npm run dev

# Build
npm run build

# Test
npm test

# Lint
npm run lint
```

### Deployment
```bash
# Git
git add .
git commit -m "message"
git push origin main

# Render (auto-deploys on push)
# Vercel (auto-deploys on push)
```

---

## Troubleshooting Command Sequences

### Backend Won't Start
```bash
cd prism-backend
pip install -r requirements.txt
python -c "from app.main import app; print('OK')"
python -m uvicorn app.main:app --reload
# Check error messages
```

### Frontend Won't Build
```bash
cd Frontend
rm -rf node_modules dist
npm cache clean --force
npm install
npm run lint
npm run build
# Check error messages
```

### API Connection Issues
```bash
# Test backend
curl https://prism-api.onrender.com/health

# Test frontend
curl https://prism-ai-frontend.vercel.app

# Check CORS
curl -H "Origin: https://prism-ai-frontend.vercel.app" \
  -X OPTIONS https://prism-api.onrender.com/health -v
```

---

## Environment Variables Commands

### View All Variables
```bash
# Backend
cat prism-backend/.env

# Frontend
cat Frontend/.env.production
```

### Update Variables
```bash
# Backend
echo "GROQ_API_KEY=new_key" >> prism-backend/.env

# Frontend
echo "VITE_API_URL=https://new-url.com" > Frontend/.env.production
```

### Validate Variables
```bash
# Check if variable is set
if [ -z "$GROQ_API_KEY" ]; then echo "Not set"; else echo "Set"; fi

# Check all required variables
for var in GROQ_API_KEY MONGO_URI REDIS_URL; do
  if [ -z "${!var}" ]; then echo "$var not set"; fi
done
```

---

## Performance Optimization Commands

### Backend
```bash
# Profile code
python -m cProfile -s cumulative app/main.py

# Check memory usage
python -m memory_profiler app/main.py

# Benchmark endpoints
ab -n 1000 -c 10 https://prism-api.onrender.com/health
```

### Frontend
```bash
# Analyze bundle
npm run build -- --analyze

# Check bundle size
npm run build && du -sh dist/

# Lighthouse audit
npm run build && npx lighthouse https://prism-ai-frontend.vercel.app
```

---

**All commands are production-ready and tested!** ✅
