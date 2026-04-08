FROM python:3.11-slim

# Install system dependencies required for ML libraries like OpenCV & Surya OCR
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libsm6 \
    libxext6 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Hugging Face Spaces strictly requires exposing port 7860
EXPOSE 7860

# Start FastAPI on port 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
