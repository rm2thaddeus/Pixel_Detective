# ML Inference FastAPI App

## Overview
This service provides image embedding and captioning endpoints using CLIP and BLIP models. It is required by the ingestion orchestration service.

## How to Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the service:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8001
   ```
   - Alternatively, you can run:
     ```bash
     python -m main
     ```
     (This requires the directory to be a module, or you may need to adjust imports.)

3. **Device selection:**
   - By default, the service will use CUDA if available. To force CPU, set the environment variable:
     ```bash
     set DEVICE_PREFERENCE=cpu  # On Windows
     export DEVICE_PREFERENCE=cpu  # On Linux/Mac
     ```

4. **Troubleshooting:**
   - If you see errors about missing models or CUDA, check your PyTorch installation and GPU drivers.
   - If you see `DeprecationWarning` about `on_event`, it is safe to ignore for now.

## Notes
- The service runs on port **8001** by default.
- This service must be running before starting the ingestion orchestration app.

---

> **@sprint-08**: Starting both backend services was problematic due to import and environment issues. Always use `uvicorn main:app` and check your Python environment. See the sprint-08 notes for more context. 