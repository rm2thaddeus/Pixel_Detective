# Backend Roadmap – December 2024

This file gathers *all* outstanding technical tasks across the two backend services so a junior developer can see, at a glance, what to tackle next and why.

---

## 🟢 Recently Completed (December 2024)

1. **Enhanced Ingestion Pipeline with Thumbnails** ✅ _Implemented 2024-12-19_
   *Change*: Added automatic thumbnail generation (200x200 JPEG) stored as base64 in Qdrant payload for fast frontend display.
   *Files*: `ingestion_orchestration_fastapi_app/routers/ingest.py`.

2. **Collection Info Endpoint** ✅ _Implemented 2024-12-19_
   *Change*: Added `/api/v1/collections/{name}/info` endpoint returning collection metadata, statistics, and sample points.
   *Files*: `ingestion_orchestration_fastapi_app/routers/collections.py`.

3. **Image Serving Endpoints** ✅ _Implemented 2024-12-19_
   *Change*: Added `/api/v1/images/{id}/thumbnail` and `/api/v1/images/{id}/info` for fast image access and metadata.
   *Files*: `ingestion_orchestration_fastapi_app/routers/images.py`.

4. **Text Search Endpoint** ✅ _Implemented 2024-12-19_
   *Change*: Added `/api/v1/search/text` for semantic text search with CLIP text embeddings.
   *Files*: `ingestion_orchestration_fastapi_app/routers/search.py`, `ml_inference_fastapi_app/main.py`.

5. **Enhanced Job Tracking** ✅ _Implemented 2024-12-19_
   *Change*: Improved job status tracking with detailed logs, progress reporting, and error handling.
   *Files*: `ingestion_orchestration_fastapi_app/routers/ingest.py`.

6. **Increase batch size end-to-end** ✅ _Implemented 2025-06-12_
   *Resolution*: Default `ML_INFERENCE_BATCH_SIZE` raised to **128** and orchestrator now queries the ML service `/api/v1/capabilities` endpoint at startup to clamp to the probed `safe_clip_batch`.  
   *Files*: `ingestion_orchestration_fastapi_app/main.py`, `ml_inference_fastapi_app/main.py`.

7. **Drop local DNG → PNG conversion** ✅ _Implemented 2025-06-12_
   *Change*: Orchestrator now sends **original RAW bytes** for `.dng` files; resize logic retained for JPEG/PNG only.  
   *Files*: `ingestion_orchestration_fastapi_app/main.py`.

8. **Parallelise SHA-256 & directory scan** ✅ _Implemented 2025-06-12_
   *Change*: SHA-256 computation is now off-loaded to `asyncio.to_thread`, reducing event-loop blocking.  
   *Files*: `ingestion_orchestration_fastapi_app/main.py`.

9. **UMAP 2-D Projection Endpoint** ✅ _Implemented 2025-06-17_
   *Change*: Added `/umap/projection` endpoint returning 2-D UMAP coordinates for scatter-plot visualisation of embeddings.
   *Files*: `ingestion_orchestration_fastapi_app/routers/umap.py`.

10. **Server-Side Upload & Scan Endpoints** ✅ _Implemented 2025-06-17_
    *Change*: Added `/api/v1/ingest/upload` (multipart file upload) and `/api/v1/ingest/scan` (absolute path ingestion) endpoints, improving UX for browser-based clients.
    *Files*: `ingestion_orchestration_fastapi_app/routers/ingest.py`.

---

## 🔴 Critical (do these first)

1. **Frontend Directory Path Integration**
   *Current issue*: Frontend can't access full system paths due to browser security restrictions. Users must manually type directory paths.
   *Potential solutions*: 
   - Implement drag-and-drop file upload with individual file processing
   - Add server-side directory browsing API for local deployments
   - Create desktop app wrapper (Electron/Tauri) that can access file system
   *Priority*: High - affects user experience significantly

2. **Error Handling Improvements**
   *Current issue*: Some error messages are not user-friendly, especially for invalid directory paths.
   *Resolution needed*: Add structured error codes and better validation messages.
   *Files*: `ingestion_orchestration_fastapi_app/routers/ingest.py`.

---

## 🟠 High (next sprint)

3. **Dynamic batch handshake endpoint in ML service** ✅ _Already implemented_
   *Status*: `GET /api/v1/capabilities` endpoint exists and returns `{ "safe_clip_batch": 471 }`.

4. **Graceful GPU lock improvements**  
   Existing `gpu_lock` works but blocks whole request. Investigate queueing or immediate *429 – try later* responses when GPU busy.

5. **Collection Management Enhancements**
   *Current gap*: No collection deletion confirmation, no collection statistics in list view.
   *Needed*: Add collection size, last modified, and usage statistics to collection listing.

6. **Search Result Pagination**
   *Current limitation*: Search results are limited but not paginated properly.
   *Needed*: Implement proper pagination with offset/limit for large result sets.

---

## 🟡 Medium

7. **Optional API key auth (local deployments can skip)**  
   Implement only when services leave localhost.

8. **Structured error codes in job status**  
   Make front-end-friendly (`ERR_DECODING_RAW`, `ERR_CLIP_INFER`, etc.).

9. **Duplicate Detection Implementation**
   *Current status*: Endpoint exists but returns placeholder response.
   *Needed*: Implement actual duplicate detection using vector similarity.

10. **Image Metadata Enhancement**
    *Current*: Basic EXIF extraction.
    *Needed*: GPS coordinates, camera settings, lens information extraction.

---

## 🟢 Nice-to-have / future

11. **Admin UI**  
    Streamlit MVP: collection list, run ingestion, tail logs.

12. **Auto-evict old cache entries**  
    Set `diskcache` size limit and culling policy.

13. **Batch Operations**
    - Bulk image deletion
    - Batch metadata updates
    - Collection merging/splitting

14. **Advanced Search Features**
    - Combined text + image similarity search
    - Metadata filtering (date ranges, camera models, etc.)
    - Saved search queries

---

## 🟣 ML Inference Service – Optimisation Roadmap

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

---

## 📊 Current System Status

### Services Running
- **Frontend**: http://localhost:3001 (Next.js 15 + TypeScript + Chakra UI with dark mode)
- **ML Inference Service**: http://localhost:8001 (CUDA-enabled, CLIP + BLIP models loaded)
- **Ingestion Orchestration**: http://localhost:8002 (all endpoints functional)
- **Qdrant Database**: localhost:6333 (collections working, thumbnails stored)

### Key Metrics (Last Benchmark)
- **25 DNG files**: 64.71s end-to-end (down from 110.78s after optimizations)
- **ML Processing**: 55.15s (15.4s decode + 39.7s inference)
- **Batch Size**: 25 (GPU safe limit: 471)
- **Success Rate**: 100% (0 failures)

### API Endpoints Status
✅ **Working**: Collection management, ingestion, search, image serving, thumbnails
✅ **Optimized**: Batch processing, caching, thumbnail generation
⚠️ **Needs Work**: Directory path input (frontend limitation), duplicate detection
❌ **Not Implemented**: Multipart uploads, caption-optional mode

---

### Recent Benchmark (baseline)

```
End-to-end ingestion: 25 DNG files in 64.71s
- Directory scan: ~1s
- ML processing: 55.15s (decode + inference)
- Qdrant upsert: ~8s
- Thumbnail generation: included in processing time
Success rate: 100% (0 failures)
```

---

**Revision history**

| Date | Author | Notes |
|------|--------|-------|
| 2025-06-12 | Senior Backend Architect (AI) | Initial roadmap with optimization priorities. |
| 2024-12-19 | AI Assistant | Updated with recent implementations: thumbnails, collection info, image serving, text search, enhanced job tracking. Added frontend integration challenges and current system status. |
| 2025-06-17 | AI Assistant | Added new UMAP projection and server-side upload/scan completions; reflected latest backend capabilities and easy-win opportunities. |