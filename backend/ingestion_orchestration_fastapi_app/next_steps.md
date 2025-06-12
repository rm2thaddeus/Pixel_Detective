# Vibe Coding - Prioritized Next Steps

## 1. Executive Summary

This document outlines a prioritized plan to enhance the `ingestion_orchestration_fastapi_app`. The focus is on improving **performance, robustness, and security**, based on the "Next Steps" section of the `README.md` and an analysis of the interaction between the ingestion service and the `ml_inference_fastapi_app`.

The key findings are:
- **Performance Bottleneck**: The primary bottleneck is in the `ml_inference_fastapi_app`. It decodes and preprocesses images from batch requests **sequentially** before running the batched model inference. This serial processing negates many of the benefits of batching.
- **Security Gap**: The internal API endpoints between the two services are currently unsecured.
- **Feature Gaps**: Collection creation is inflexible, and error reporting could be more detailed for easier debugging.

The following plan addresses these points in order of priority.

---

## Status Update – 2025-06-12 (post-optimisation)

The first optimisation wave (larger batch size, RAW passthrough, threaded SHA-256) cut end-to-end ingestion time from **110.78 s → 64.71 s** for 25 DNG images (≈ 1.7× faster). The ML service now finishes the single 25-image batch in **55.15 s** (15.4 s decode + 39.7 s inference).

All tasks in **Priority 1** are now **✔ Completed**.  Remaining opportunities are listed below.

---

## 2. Priority 1 (New) — Quick-Win Performance Ideas

1. **Skip captioning during ingestion (optional, async later)**  
   • BLIP load + captioning costs ≈ 7 s + inference time each batch.  
   • Write embeddings immediately, enqueue captions to a separate job/queue; search can function with embeddings only.  
   **Expected gain**: ~10-15 s per 25 images.

2. **Move image decoding to ingestion host**  
   • Decoding σ 15 s happens on GPU box CPU threads; doing it on ingestion host (already reading bytes) and sending RGB PNG/JPEG would overlap I/O and shrink ML-side latency.  
   **Trade-off**: more network bytes (~25-30 MB) but LAN is >1 Gbps.

3. **Multipart / streaming payloads (remove Base64)**  
   • Current JSON+Base64 inflates payload ≈ 33 % and costs encode/-decode CPU.  
   • Switch to `multipart/form-data` or HTTP/2 streaming; expect ~2-3 s off network + CPU per 25 images.

4. **Pinned-memory DataLoader & `torch.compile` for CLIP**  
   • Torch 2 allows `torch.compile` with `mode="reduce-overhead"`. Early tests show 10-15 % speed-up on ViT-B/32 in fp16.  
   • Also use `pin_memory=True` when stacking tensors to cut host-→GPU transfer latency.

5. **Metadata extractor fast-path for DNG**  
   • Current extractor tries PIL on `.dng`, raises `cannot identify image` for every file (see logs). Add early exit to skip PIL and avoid noisy logs + exception overhead.

6. **GPU utilisation**  
   • For 25-image batch the GPU is under-utilised (batch safe limit 471).  In large ingestions (>128) we already fill the GPU.  Consider `ML_INFERENCE_BATCH_SIZE = min(safe_batch, 256)`.

---

## 3. Priority 2: High - Security

### Task 2.1: (Optional) Secure Service-to-Service API with an API Key

- **Justification**: The ML inference endpoint is open to anyone on the network. A simple, shared API key will ensure that only the ingestion service can make requests to it, providing a crucial layer of security. *For local/off-line usage this can be postponed, but is recommended before any network exposure.*
- **Files to Modify**:
    - `backend/ml_inference_fastapi_app/main.py` (to check for the key)
    - `backend/ingestion_orchestration_fastapi_app/main.py` (to send the key)
- **Action**:
    1.  **In the ML Service (`ml_inference_fastapi_app`)**:
        -   Add a `SECRET_API_KEY` loaded from an environment variable.
        -   Create a FastAPI dependency that checks for an `x-api-key` header and compares it to the secret key.
        -   Add this dependency to the `/batch_embed_and_caption` endpoint.
    2.  **In the Ingestion Service (`ingestion_orchestration_fastapi_app`)**:
        -   Load the same `SECRET_API_KEY` from an environment variable.
        -   When making requests with `httpx`, include the key in the headers: `headers={"x-api-key": THE_SECRET_KEY}`.

---

## 4. Priority 3: Medium - Future Features

### Task 3.1: Plan for a Web-Based User Interface

- **Justification**: A UI would make the service accessible to non-technical users and simplify the management of collections and ingestion jobs, as noted in the README.
- **Action**: This is a larger effort that should be its own project. A recommended approach would be:
    - **Framework Choice**: Use a simple, data-oriented Python framework like **Streamlit** or a modern JavaScript framework like **React** or **Vue**.
    - **Core Features**:
        1.  **Dashboard**: View all collections and their status.
        2.  **Collection Management**: Create (with custom parameters) and delete collections.
        3.  **Ingestion**: A file/directory picker to start a new ingestion job.
        4.  **Job Status Viewer**: A page to view the live logs and progress of an ongoing job and the results of completed jobs.
- **File to Create**: A new directory, e.g., `frontend/admin_ui`, would house this new application.