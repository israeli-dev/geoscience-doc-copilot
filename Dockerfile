# Use Python 3.11 slim - Render + Cloud Run compatible
FROM python:3.11-slim

WORKDIR /app

# Install system deps for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_backend.txt .
RUN pip install --no-cache-dir -r requirements_backend.txt

COPY . .

# Render and Cloud Run both use PORT env (Render 10000, Cloud Run 8080)
ENV PORT=8080
EXPOSE 8080

# FIX: Use root main.py (main:app) - works for both Render and Cloud Run
# Your old Dockerfile used app.main:app but app/main.py doesn't exist - caused "Exited with status 1"
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
