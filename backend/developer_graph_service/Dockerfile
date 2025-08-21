FROM python:3.11-slim
WORKDIR /app
# Install service-specific dependencies
COPY backend/developer_graph_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
# Copy source
COPY developer_graph /app/developer_graph
COPY backend/developer_graph_service/main.py /app/main.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
