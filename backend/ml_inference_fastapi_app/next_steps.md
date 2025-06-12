# Vibe Coding - ML Inference Service Prioritized Next Steps

*Document version: 2025-06-12*

This roadmap complements `backend/DEVELOPER_ROADMAP.md` and drills into the **ML Inference Service** (`backend/ml_inference_fastapi_app`). Items are triaged by *wall-time impact per 25-image batch*.

---

## 1. Status Snapshot

| Stage | Time (s) | Notes |
|-------|---------|-------|
| Decode & preprocess | **15.4** | 8 CPU threads (`ThreadPoolExecutor`) |
| CLIP fp16 encode | **39.7** | Batch size 25, GPU safe 471 |
| BLIP load & caption | **~7** | One-off per process |
| **Total** | **55.1** | For 25 DNG images |

Target: **≤ 30 s** per 25 images (another ~45 % cut).

---

## 2. 🔴 Critical (next sprint)

1. **Caption-optional mode**  
   *Why*: BLIP adds ~7 s fixed + GPU time. Not always needed for vector search.  
   *What*: Honour `DISABLE_CAPTIONS=1`; in that mode return `caption=None` quickly.  
   *How*:  
   • Wrap BLIP branch in `if not os.getenv("DISABLE_CAPTIONS"):`.  
   • Adjust Pydantic response (caption may be null).  
   *Gain*: **7–10 s** (≈ 15 %).  
   *Touched*: `main.py` (`batch_embed_and_caption`, single-image `/caption`).

2. **Multipart / streaming uploads**  
   *Why*: JSON+Base64 inflates payload 33 %, costs encode/decode CPU.  
   *What*: New `/batch_embed_and_caption_multipart` accepting `multipart/form-data` (`files[]`).  
   *Client*: change orchestrator's `_send_batch_to_ml_service`.  
   *Gain*: **2–3 s** for 25 images; larger for big jobs.

3. **Pinned memory tensors + `torch.compile`**  
   *Why*: Reduce host→GPU copy & kernel overhead.  
   *What*:  
   • When stacking tensors: `torch.stack(..., pin_memory=True).to(device, non_blocking=True)`.  
   • After CLIP load: `clip_model_instance = torch.compile(clip_model_instance, mode="reduce-overhead")`.  
   *Gain*: **10–15 %** of CLIP time (~4 s).

---

## 3. 🟠 High

4. **Metadata extractor fast-path for DNG**  
   Skip PIL attempt to avoid `cannot identify image` exceptions.  
   *Files*: `utils/metadata_extractor.py`.  
   *Gain*: 1–2 s + quieter logs.

5. **Dynamic batch utilisation**  
   Use `min(safe_batch, 256)` to keep GPU >50 % utilised on small jobs without risking OOM on large ones.

---

## 4. 🟡 Medium / Research

6. **Bits-and-Bytes 8-bit BLIP**  
   Cut VRAM & caption latency 30 %.

7. **CLIP ONNX / TensorRT**  
   Encoder speed-up 1.3–1.6×; requires export & CUDA 11.8 toolchain.

8. **gRPC or HTTP/2 streaming responses**  
   Overlap network, inference and DB upsert.

---

## 5. Task Breakdown & Estimates

| ID | Task | Effort | Owner |
|----|------|--------|-------|
| C-1 | Caption-optional env flag | 0.5 d | Backend | 
| C-2 | Multipart endpoint + client | 3 d | Backend | 
| C-3 | `torch.compile` & pin-mem | 0.5 d | AI Engineer | 
| H-4 | Metadata fast-path | 0.25 d | Backend | 
| H-5 | Batch size heuristic | 0.25 d | Backend | 

*After critical items we expect total time **≈ 25–30 s** per 25 images, matching the stretch goal.* 