FROM rapidsai/base:24.08-cuda12.2-py3.11

# Set working directory
WORKDIR /app

# Install additional Python dependencies that are **not** already provided by the RAPIDS image.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose port and launch FastAPI with auto-reload (overridden in docker-compose.dev)
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
