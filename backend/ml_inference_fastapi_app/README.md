# ML Inference FastAPI App

## Overview
This service provides image embedding and captioning endpoints using CLIP and BLIP models. It is required by the ingestion orchestration service.

## Requirements
- Python 3.8 or higher
- Optional: GPU with CUDA support and compatible PyTorch
- Internet connection for downloading model weights

## Setup & Installation
1. Navigate to this folder:
   ```bash
   cd backend/ml_inference_fastapi_app
   ```
2. (Optional) Create and activate a virtual environment:
   - Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - macOS/Linux:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
- `DEVICE_PREFERENCE` (default: `cuda`): choose `cuda` or `cpu`
  - Windows CMD: `set DEVICE_PREFERENCE=cpu`
  - PowerShell: `$Env:DEVICE_PREFERENCE = 'cpu'`
  - macOS/Linux: `export DEVICE_PREFERENCE=cpu`
- `LOG_LEVEL` (default: `INFO`): e.g., `DEBUG`, `INFO`, `WARNING`
- `PORT` (default: `8001`): port number for the service

## Running the Service

**Development Mode** (auto-reload on code changes):
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

**Production Mode**:
```bash
python main.py
```
> By default, `python main.py` runs Uvicorn on `0.0.0.0:${PORT}` with reload disabled.

## Quickstart Examples

- **Health Check**:
  ```bash
  curl http://localhost:8001/
  ```

- **Embed an Image**:
  ```bash
  curl -X POST http://localhost:8001/api/v1/embed \
    -H "Content-Type: application/json" \
    -d '{"image_base64":"<BASE64_IMAGE>","filename":"test.jpg"}'
  ```

- **Caption an Image**:
  ```bash
  curl -X POST http://localhost:8001/api/v1/caption \
    -H "Content-Type: application/json" \
    -d '{"image_base64":"<BASE64_IMAGE>","filename":"test.jpg"}'
  ```

## Troubleshooting
- If models fail to load at startup, review logs and verify `CLIP_MODEL_NAME` and `BLIP_MODEL_NAME` environment variables.
- For CUDA issues, force CPU by setting `DEVICE_PREFERENCE=cpu`.
- If port `8001` is in use, set `PORT` to an available port.

## Notes
- The service runs on port **8001** by default.
- This service must be running before starting the ingestion orchestration app.

---

> **@sprint-08**: Starting both backend services was problematic due to import and environment issues. Always use `uvicorn main:app` and check your Python environment. See the sprint-08 notes for more context. 