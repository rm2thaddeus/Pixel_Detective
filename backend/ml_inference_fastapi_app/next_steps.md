# Vibe Coding - ML Inference Service Prioritized Next Steps

## 1. Executive Summary

This document outlines a prioritized plan to enhance the `ml_inference_fastapi_app`. The focus is on improving **GPU memory management, security, and concurrency control**, based on an analysis of the current implementation.

Following the recent refactor to parallelize image preprocessing, the most critical performance bottleneck has been resolved. The next steps address the remaining architectural weaknesses to make the service more robust, secure, and efficient for production use.

The key findings are:
- **High Idle Memory Usage**: The BLIP model for captioning is loaded eagerly at startup, consuming significant GPU memory even when not in use.
- **Security Gap**: The API endpoints are unsecured, allowing any service on the network to make requests.
- **Concurrency Risk**: While individual model calls are atomic, there is no mechanism to prevent multiple API requests from attempting to use the GPU simultaneously, risking out-of-memory (OOM) errors.

The following plan addresses these points in order of priority.

---

## 2. Priority 1: High - GPU Memory Optimization

### Task 2.1: Implement Lazy Loading for BLIP Model

- **Justification**: The BLIP model is only needed for the captioning-related functions. Eagerly loading it at startup reserves a large amount of VRAM that could be better used by CLIP for processing larger batches or for other processes on the machine. Lazy-loading will ensure it's only placed on the GPU when a captioning request is actually made.
- **File to Modify**: `backend/ml_inference_fastapi_app/main.py`
- **Action**:
    1.  Modify the `startup_event` to only load the CLIP model.
    2.  Create a new dependency or helper function (e.g., `get_blip_model()`).
    3.  Inside this function, check if the global `blip_model_instance` is `None`. If it is, load the model and processor from Hugging Face and store them in the global variables.
    4.  In all endpoints that use BLIP (`/caption`, `/batch_embed_and_caption`), `yield` or `await` this new function to ensure the model is loaded before use.
    5.  (Optional) Add logic to offload the BLIP model from memory after a period of inactivity.

---

## 3. Priority 2: High - Security

### Task 3.1: Secure Service-to-Service API with an API Key

- **Justification**: The inference endpoints should not be open to the public network. A simple, shared API key provides a necessary layer of authentication, ensuring that only trusted clients (like the Ingestion Orchestration Service) can use its resources.
- **Files to Modify**:
    - `backend/ml_inference_fastapi_app/main.py` (to check for the key)
    - `backend/ingestion_orchestration_fastapi_app/main.py` and `dependencies.py` (to send the key)
- **Action**:
    1.  **In the ML Service (`ml_inference_fastapi_app`)**:
        -   Define a `SECRET_API_KEY` loaded from an environment variable.
        -   Create a FastAPI dependency that requires an `x-api-key` header and validates it against the secret.
        -   Protect all v1 routes with this dependency.
    2.  **In the Ingestion Service (`ingestion_orchestration_fastapi_app`)**:
        -   Load the same `SECRET_API_KEY` from an environment variable.
        -   Modify the `httpx` client logic to include `headers={"x-api-key": THE_SECRET_KEY}` in all requests to the ML service.

---

## 4. Priority 3: Medium - Robustness

### Task 4.1: Implement a GPU Lock for Concurrency Control

- **Justification**: Without a locking mechanism, two separate, concurrent calls to the batch endpoint could each try to load a full batch of images onto the GPU, leading to a race condition and a likely OOM error. An `asyncio.Lock` ensures that only one inference task can access the GPU at a time.
- **File to Modify**: `backend/ml_inference_fastapi_app/main.py`
- **Action**:
    1.  Create a global `asyncio.Lock` instance (e.g., `gpu_lock = asyncio.Lock()`).
    2.  In the `batch_embed_and_caption_endpoint_v1` function, wrap the model inference sections (the calls to `_encode_clip` and `_generate_blip`) in an `async with gpu_lock:` block.
    3.  This will ensure that even if multiple requests are preprocessing images in parallel, only one will proceed to the GPU-intensive step at a time, preventing memory clashes.

  **Conceptual Code Change:**
  ```python
  # In backend/ml_inference_fastapi_app/main.py

  gpu_lock = asyncio.Lock()

  @v1_router.post("/batch_embed_and_caption", ...)
  async def batch_embed_and_caption_endpoint_v1(request: ...):
      # ... parallel preprocessing ...

      async with gpu_lock:
          # --- CLIP Embeddings ---
          # ... inference logic ...

          # --- BLIP Captions ---
          # ... inference logic ...

      # ... combine results ...
  ```

</rewritten_file> 