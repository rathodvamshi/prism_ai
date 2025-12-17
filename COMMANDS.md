# 📋 COPY-PASTE RENDER COMMANDS

## 🔥 BACKEND API SERVICE

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
python -m gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT
```

**Root Directory:**
```
prism-backend
```

## 🔄 CELERY WORKER SERVICE

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
python -m celery -A app.core.celery_app worker --loglevel=info --queues=email,default --concurrency=1
```

**Root Directory:**
```
prism-backend
```

## 🎨 VERCEL FRONTEND

**Install Command:**
```
cd Frontend && npm install
```

**Build Command:**
```
cd Frontend && npm run build
```

**Output Directory:**
```
Frontend/dist
```

**Root Directory:**
```
./
```

## 🚨 IF RENDER BLOCKS MANUAL SETUP:

Try **Blueprint deployment** instead:
1. New → Blueprint  
2. Connect repo
3. Use `render.yaml` file
4. Deploy automatically