# PetroLens Executive v3.1 - Backend API + Frontend Ready
FROM python:3.11-slim

WORKDIR /app

# System deps for PyMuPDF + python-docx
RUN apt-get update && apt-get install -y \
    build-essential \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose both FastAPI and Streamlit
EXPOSE 8000 8501

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
