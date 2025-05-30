# Define base image
FROM python:3.9-slim

# Set up working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ingestion_orchestration_fastapi_app/. .
COPY utils ../utils

# Define CMD to run Uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]

EXPOSE 8002 