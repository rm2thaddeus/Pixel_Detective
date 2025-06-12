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

## 🟣 ML Inference Service – Optimisation Roadmap (added 2025-06-12)

Priorities are ordered by *estimated wall-time reduction per 25-image batch* on a 6 GB GPU box.

### 🔴 Critical (next sprint – aim ≥ 30 % gain)

1. **Caption-optional mode**  
   • Skip BLIP captioning during ingestion when `DISABLE_CAPTIONS=1`.  
   • Captions can be produced later via an async job.  
   *Expected gain*: **7–10 s** / batch (~15 %).  
   *Files*: `ml_inference_fastapi_app/main.py` (`batch_embed_and_caption`, new env flag).

2. **Multipart / streaming uploads**  
   • Replace JSON + Base64 with `multipart/form-data` endpoint; drop encode/decode & 33 % payload bloat.  
   *Gain*: **2–3 s** for 25 images; larger for big imports.  
   *Files*: `ml_inference_fastapi_app/main.py`, `ingestion_orchestration_fastapi_app/main.py` (client changes).

3. **Pinned-memory tensors + `torch.compile` for CLIP**  
   • `clip_model = torch.compile(clip_model, mode="reduce-overhead")`.  
   • When stacking tensors use `pin_memory=True` & `non_blocking=True`.  
   *Gain*: **10–15 %** GPU throughput (~4 s).  
   *Files*: `ml_inference_fastapi_app/main.py` (model load & inference helpers).

### 🟠 High (nice speed-ups, lower effort)

4. **Fast-path metadata extractor for DNG**  
   • Skip PIL attempt; directly return basic stats for `.dng` to silence exceptions.  
   *Gain*: 1-2 s and cleaner logs.  
   *Files*: `utils/metadata_extractor.py`.

5. **Fine-tune dynamic batch sizing**  
   • Use `ML_INFERENCE_BATCH_SIZE = min(safe_batch, 256)` to keep GPU ≥ 50 % utilised on small jobs while avoiding OOM on big jobs.  
   *Gain*: ~1 s for tiny jobs; stability for large ones.

### 🟡 Medium (engineering-heavier)

6. **8-bit / 4-bit BLIP weights via bitsandbytes** (-30 % caption latency & memory).  
7. **CLIP ONNX or TensorRT path** (1.3-1.6× encoder speed).

> Detailed implementation notes live in `ml_inference_fastapi_app/next_steps.md`.

---

### Recent Benchmark (baseline)

```