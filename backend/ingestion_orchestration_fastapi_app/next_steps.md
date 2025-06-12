# Vibe Coding - Prioritized Next Steps

## 1. Executive Summary

This document outlines a prioritized plan to enhance the `ingestion_orchestration_fastapi_app`. The focus is on improving **performance, robustness, and security**, based on the "Next Steps" section of the `README.md` and an analysis of the interaction between the ingestion service and the `ml_inference_fastapi_app`.

The key findings are:
- **Performance Bottleneck**: The primary bottleneck is in the `ml_inference_fastapi_app`. It decodes and preprocesses images from batch requests **sequentially** before running the batched model inference. This serial processing negates many of the benefits of batching.
- **Security Gap**: The internal API endpoints between the two services are currently unsecured.
- **Feature Gaps**: Collection creation is inflexible, and error reporting could be more detailed for easier debugging.

The following plan addresses these points in order of priority.

---

## Status Update – 2025-06-12

The RAW-filename bug has been fixed and the pipeline successfully processed 25 DNG images in ~111 s (down from >170 s with 100 % failures).  Logs show that the ML service currently receives four requests of 8, 8, 8 and 1 images respectively, and each GPU inference call takes ≈11 s.  

Key findings after the latest run:

* **Decoding Parallelisation is already implemented** in `ml_inference_fastapi_app` via a `ThreadPoolExecutor`; therefore the old Task 1.1 is now **✔ Completed**.
* **Main bottleneck** is now the *small batch size* (8) chosen by the ingestion service compared to the safe GPU batch size (≈471) probed by the ML service.
* **Redundant DNG → PNG conversion** is still happening in the ingestion service; ML service can decode RAW directly, so we are double-decoding every file.

We therefore revise the roadmap below.

---

## 2. Priority 1: Critical — Performance & Robustness

### Task 1.1 ✔ (Completed) – Parallel image preprocessing in ML service
The `ThreadPoolExecutor` & `asyncio.as_completed` implementation in `ml_inference_fastapi_app/main.py` already preprocesses images concurrently.

### Task 1.2 — Increase end-to-end batch size

* **Justification**: GPU safe batch size is ≈ 471 but we currently send just **8 images**. 25 images therefore incur **4 full GPU passes** (~44 s), while a single 25-image call would cost ~13 s.  
* **Change**: Bump `ML_INFERENCE_BATCH_SIZE` default from 8 → 128 (configurable).  Provide an optional *hand-shake* endpoint in ML service that returns its probed safe batch size so the orchestrator can adapt dynamically.
* **Files**: `backend/ingestion_orchestration_fastapi_app/main.py` (change batching logic & env var doc) + optional `/api/v1/capabilities` in ML service.

### Task 1.3 — Remove redundant DNG→PNG conversion in ingestion service

* **Justification**: We currently decode RAW files with `rawpy` in the ingestion service and again decode the resulting PNG in the ML service, doubling CPU & I/O.  
* **Change**: Send the **original bytes** for RAW images, drop the local decode step, and rely solely on ML service for DNG handling.  Only JPEG/PNG resizing remains client-side (optional).
* **Expected Gain**: ~35 % reduction in CPU wall-time on host and less memory pressure.

### Task 1.4 — Smarter directory walker & hash computation

* Parallelise SHA-256 computation using `aiofiles` + `asyncio.to_thread` workers.  This can overlap I/O with CPU and prepare batches faster when ingesting thousands of images.

---

### Benchmark Evidence

Terminal output confirming current baseline:

```
Ingestion completed in 110.78 seconds.
Result: total_processed=25, total_failed=0
GPU logs: four inference passes (8 + 8 + 8 + 1 images) at ~11 s per pass.
```

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