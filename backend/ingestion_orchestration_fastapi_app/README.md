# Ingestion Orchestration FastAPI App

## Prerequisites

1. **Qdrant vector database**:
   - **Docker (Linux/macOS)**:
     ```bash
     docker run -p 6333:6333 -p 6334:6334 \
       -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
       qdrant/qdrant:latest
     ```
   - **Docker (Windows PowerShell)**:
     ```powershell
     docker run -p 6333:6333 -p 6334:6334 `
       -v "${PWD}/qdrant_storage:/qdrant/storage:z" `
       qdrant/qdrant:latest
     ```
   - **Docker (Windows CMD)**:
     ```cmd
     docker run -p 6333:6333 -p 6334:6334 -v %cd%/qdrant_storage:/qdrant/storage:z qdrant/qdrant:latest
     ```
   - **Python client (Local Mode)**:
     ```bash
     pip install qdrant-client
     python - <<EOF
     from qdrant_client import QdrantClient, models
     client = QdrantClient(url="http://localhost:6333")
     if not client.get_collections().collections:
         client.create_collection(
             collection_name="development_test",
             vectors_config=models.VectorParams(size=512, distance=models.Distance.COSINE)
         )
     EOF
     ```

2. **ML Inference Service** running on port 8001:
   ```bash
   uvicorn backend.ml_inference_fastapi_app.main:app --host 0.0.0.0 --port 8001
   ```

## Overview
This service handles ingestion orchestration, metadata extraction, and communication with Qdrant and the ML inference service.

### Environment Variables

- `QDRANT_UPSERT_BATCH_SIZE` – number of points to send to Qdrant in a single bulk upsert. Default: `32`.

## How to Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the service:**
   **You must run this from the project root!**
   ```bash
   uvicorn backend.ingestion_orchestration_fastapi_app.main:app --host 0.0.0.0 --port 8002
   ```
   - Running from inside the `ingestion_orchestration_fastapi_app` directory (e.g., `uvicorn main:app ...`) will fail due to Python import/package rules.

3. **Troubleshooting:**
   - If you see an error like:
     ```
     ImportError: attempted relative import with no known parent package
     ```
     or
     ```
     ImportError: cannot import name 'get_qdrant_dependency' from partially initialized module ... (circular import)
     ```
     Make sure you:
     - Run from the project root with the full module path as above.
     - Have the latest `qdrant-client` (>=1.3.0) installed.
   - If you see:
     ```
     ImportError: cannot import name 'SortOrder' from 'qdrant_client.http.models'
     ```
     Upgrade your Qdrant client:
     ```bash
     pip install --upgrade "qdrant-client>=1.3.0"
     ```

## Notes
- The service runs on port **8002** by default.
- It requires a running Qdrant instance and the ML inference service (see sibling directory).

---

> **@sprint-08**: There was significant trouble starting this service due to Python's relative import rules and circular import issues. Always use the full module path from the project root, and ensure your dependencies are up to date. See the sprint-08 notes for more context. 