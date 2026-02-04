# Ingestion Orchestration Service - Agent Guidelines

## 🎯 **Service Purpose**

The Ingestion Orchestration Service coordinates the entire image processing pipeline:
- Scans directories for images
- Manages deduplication via SHA-256 hashing
- Coordinates ML service calls for embeddings/captions
- Generates thumbnails
- Upserts data to Qdrant vector database

**Port**: 8002  
**Technology**: FastAPI, AsyncIO, Qdrant Client

---

## 🏗️ **Pipeline Architecture**

### **4-Stage Concurrent Pipeline**

```
Stage 1: IO Scanner
  ↓ raw_queue
Stage 2: CPU Processor (file reading, hashing, cache check)
  ↓ ml_queue
Stage 3: GPU Worker (ML service calls, batching)
  ↓ db_queue  
Stage 4: DB Upserter (Qdrant batch upsert)
```

### **Key Components**

| Component | File | Responsibility |
|-----------|------|---------------|
| **Pipeline Manager** | `pipeline/manager.py` | Orchestrates all stages, manages job state |
| **IO Scanner** | `pipeline/io_scanner.py` | Scans directories, queues file paths |
| **CPU Processor** | `pipeline/cpu_processor.py` | Hashing, cache checks, metadata extraction |
| **GPU Worker** | `pipeline/gpu_worker.py` | Batches and calls ML service |
| **DB Upserter** | `pipeline/db_upserter.py` | Batches and upserts to Qdrant |

---

## 🔧 **Common Development Tasks**

### **Adding a New Router Endpoint**

1. **Create function in appropriate router** (`routers/`)
2. **Use dependency injection**:
```python
from fastapi import APIRouter, Depends
from ..dependencies import get_qdrant_client, get_active_collection

router = APIRouter(prefix="/api/v1/my-endpoint")

@router.get("/")
async def my_endpoint(
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection: str = Depends(get_active_collection)
):
    # Endpoint logic
```

3. **Include router in main.py**:
```python
from .routers import my_router
app.include_router(my_router.router)
```

### **Modifying the Pipeline**

**To change a pipeline stage:**

1. **Identify the stage file** (`pipeline/*.py`)
2. **Understand the queue contract**:
   - What data format comes in?
   - What data format goes out?
   - When to send sentinel (None)?
3. **Modify the stage logic**
4. **Update JobContext** if adding new metrics
5. **Test with small dataset first**

**Example: Adding new metadata field**

```python
# In cpu_processor.py
metadata = await loop.run_in_executor(None, utils.extract_image_metadata, file_path)

# Add new field
metadata["my_new_field"] = await compute_new_field(file_path)

# Pass to ml_queue
await ctx.ml_queue.put({
    "file_hash": file_hash,
    "metadata": metadata,  # Now includes new field
    ...
})
```

### **Adjusting Batch Sizes**

Batch sizes are **automatically negotiated** at startup:

```python
# In pipeline/manager.py
ml_caps = get_latest_ml_capabilities(ML_SERVICE_URL)
safe_clip_batch_size = ml_caps.get("safe_clip_batch", 32)
```

**Manual override** (for testing):
```bash
export ML_INFERENCE_BATCH_SIZE=64
export QDRANT_UPSERT_BATCH_SIZE=128
```

---

## 📊 **Key Patterns**

### **1. Background Job Pattern**

```python
from fastapi import BackgroundTasks
from ..pipeline import manager

@router.post("/ingest", status_code=202)
async def start_ingestion(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    qdrant: QdrantClient = Depends(get_qdrant_client)
):
    job_id = await manager.start_pipeline(
        directory_path=request.directory_path,
        collection_name=get_active_collection(),
        background_tasks=background_tasks,
        qdrant_client=qdrant
    )
    
    return {"job_id": job_id, "status": "started"}

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job_ctx = manager.get_job_status(job_id)
    if not job_ctx:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_ctx
```

### **2. Cache Pattern**

```python
import diskcache

cache = diskcache.Cache('.diskcache')

# Check cache before processing
cache_key = f"{collection_name}:{file_hash}"
cached_data = cache.get(cache_key)

if cached_data:
    # Use cached result
    point = PointStruct(
        id=cached_data["id"],
        vector=cached_data["vector"],
        payload=cached_data["payload"]
    )
else:
    # Process and cache
    result = await process_image(file_path)
    cache.set(cache_key, {
        "id": point_id,
        "vector": embedding,
        "payload": metadata
    })
```

### **3. Service-to-Service Communication**

```python
import httpx

async def send_batch_to_ml_service(batch_items: list[dict]) -> list[dict]:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{ML_SERVICE_URL}/api/v1/batch_embed_and_caption",
            json={"images": batch_items}
        )
        response.raise_for_status()
        return response.json()["results"]
```

---

## 🐛 **Debugging Checklist**

### **Pipeline Stalls**

- [ ] Check all queues have proper sentinel handling
- [ ] Verify ML service is responding (`/health`)
- [ ] Check GPU worker logs for OOM errors
- [ ] Confirm Qdrant is accessible
- [ ] Review worker counts vs queue sizes

### **Performance Issues**

- [ ] Check batch sizes are properly negotiated
- [ ] Verify cache hit rate (`ctx.cached_files` in logs)
- [ ] Monitor GPU utilization (`nvidia-smi`)
- [ ] Check network latency to ML service
- [ ] Review thumbnail generation time

### **Failed Ingestion**

- [ ] Check directory path is accessible
- [ ] Verify supported image formats
- [ ] Check ML service logs for errors
- [ ] Verify Qdrant collection exists
- [ ] Review job logs for specific errors

---

## ⚠️ **Critical Warnings**

### **Never Do**

❌ **Import main.py** from routers - Use dependency injection  
❌ **Block event loop** - Use `asyncio.to_thread()` for CPU work  
❌ **Skip cache checks** - Always check before processing  
❌ **Ignore ML capabilities** - Query before batching  
❌ **Forget sentinels** - Queue shutdown requires None signals  

### **Always Do**

✅ **Use dependency injection** - `Depends(get_qdrant_client)`  
✅ **Async for I/O** - File reading, network calls  
✅ **Batch operations** - Both ML calls and Qdrant upserts  
✅ **Error logging** - Include job_id in all logs  
✅ **Progress tracking** - Update JobContext regularly  

---

## 📈 **Performance Benchmarks**

**Current Metrics** (25 DNG files):
- Total time: ~65 seconds
- ML processing: ~55 seconds (85% of total)
- Qdrant upsert: ~8 seconds (12% of total)
- Cache hit rate: 80%+ on repeated ingestion

**Optimization Targets**:
- Reduce ML time with larger batches
- Improve thumbnail generation parallelism
- Optimize metadata extraction

---

**Last Updated**: Sprint 11  
**Status**: Production Ready  
**Maintainer**: Backend Team

