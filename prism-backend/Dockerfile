# Use official lightweight Python image
FROM python:3.10-slim

# Install System Dependencies (FFmpeg for Audio, Curl for Healthchecks)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Work Directory
WORKDIR /app

# Copy Requirements & Install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Code
COPY . .

# Expose Port
EXPOSE 8000

# Start Command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]