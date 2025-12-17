# Use official lightweight Python image
FROM python:3.10-slim

# Install System Dependencies (FFmpeg for Audio, Curl for Healthchecks, Playwright deps)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    libnss3 \
    libnspr4 \
    libgbm1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Set Work Directory
WORKDIR /app

# Copy Requirements & Install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Browser (Chromium)
RUN playwright install chromium
RUN playwright install-deps

# Copy Code
COPY . .

# Expose Port
EXPOSE 8000

# Start Command (production-ready: gunicorn with uvicorn workers)
CMD ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]