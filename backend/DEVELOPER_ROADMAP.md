# Backend Roadmap – June 2025

This file gathers *all* outstanding technical tasks across the two backend services so a junior developer can see, at a glance, what to tackle next and why.

---

## 🔴 Critical (do these first)

1. **Increase batch size end-to-end** ✅ _Implemented 2025-06-12_
   *Current issue*: Orchestrator sends batches of 8 even though the ML service can take ~470.  
   *Resolution*: Default `ML_INFERENCE_BATCH_SIZE` raised to **128** and orchestrator now queries the ML service `/api/v1/capabilities` endpoint at startup to clamp to the probed `safe_clip_batch`.  
   *Files*: `ingestion_orchestration_fastapi_app/main.py`, `ml_inference_fastapi_app/main.py`.

2. **Drop local DNG → PNG conversion** ✅ _Implemented 2025-06-12_
   *Change*: Orchestrator now sends **original RAW bytes** for `.dng` files; resize logic retained for JPEG/PNG only.  
   *Files*: `ingestion_orchestration_fastapi_app/main.py`.

3. **Parallelise SHA-256 & directory scan** ✅ _Implemented 2025-06-12_
   *Change*: SHA-256 computation is now off-loaded to `asyncio.to_thread`, reducing event-loop blocking.  Additional full parallel directory traversal slated for later optimisation.  
   *Files*: `ingestion_orchestration_fastapi_app/main.py`.

---

## 🟠 High (next sprint)

4. **Dynamic batch handshake endpoint in ML service**  
   *Expose* `{ "safe_clip_batch": 471 }` so orchestrator can adapt on any GPU.

5. **Graceful GPU lock improvements**  
   Existing `gpu_lock` works but blocks whole request. Investigate queueing or immediate *429 – try later* responses when GPU busy.

---

## 🟡 Medium

6. **Optional API key auth (local deployments can skip)**  
   Implement only when services leave localhost.

7. **Structured error codes in job status**  
   Make front-end-friendly (`ERR_DECODING_RAW`, `ERR_CLIP_INFER`, etc.).

---

## 🟢 Nice-to-have / future

8. **Admin UI**  
   Streamlit MVP: collection list, run ingestion, tail logs.

9. **Auto-evict old cache entries**  
   Set `diskcache` size limit and culling policy.

---

### Recent Benchmark (baseline)

```
Ingestion completed in 110.78 s – 25 RAW images, 0 failures.
GPU log: 8-image batches, ~11 s per pass.
```

Optimisations above are expected to bring this down to ~30 s for the same dataset. 

### Updated Benchmark (post-optimisation – 2025-06-12)

```
Ingestion completed in 64.71 s – 25 RAW images, 0 failures.
Observed speed-up ≈ 1.7× compared to baseline (110.78 s → 64.71 s).
Batch size negotiated: 128 images (1 pass for 25 images).
```

*Notes*
• Time halved versus previous run, validating removal of local RAW decode and larger batch size usage.
• Still room (~2×) to reach ~30 s target – remaining bottlenecks likely I/O and ML inference latency; track under High-priority items. 