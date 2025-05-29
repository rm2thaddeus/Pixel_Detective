# Stage 1: Build stage - with build tools and potentially larger base image if needed
FROM python:3.9-slim as builder

WORKDIR /app

# Install git and other build dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends git gcc

# Copy requirements and install them
# This layer is cached if requirements.txt doesn't change
COPY ./requirements.txt /app/requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Final stage - a slim image with only runtime dependencies
FROM python:3.9-slim

WORKDIR /app

# Copy installed packages from the builder stage
COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install the wheels - this should be faster as they are pre-built
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

# Copy the application code
COPY . /app

# Make port 8001 available
EXPOSE 8001

# Run main.py when the container launches
# Ensure PYTHONUNBUFFERED is set for logs (can also be in docker-compose.yml)
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"] 