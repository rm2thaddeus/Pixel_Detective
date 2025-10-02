# Backend Development - Agent Guidelines

## 🎯 **Overview**

This document provides comprehensive guidelines for AI agents working on the **Pixel Detective backend services**. The backend consists of three microservices working together to provide AI-powered media search capabilities.

---

## 🏗️ **Backend Architecture**

### **Services Overview**

```
Backend Stack (Pixel Detective)
├── Ingestion Orchestration (Port 8002)
│   ├── Pipeline coordination
│   ├── Collection management
│   ├── Thumbnail generation
│   └── Qdrant integration
│
├── ML Inference (Port 8001)
│   ├── CLIP embeddings
│   ├── BLIP captions
│   ├── GPU management
│   └── Batch processing
│
├── GPU-UMAP Service (Port 8003)
│   ├── RAPIDS cuML acceleration
│   ├── UMAP projections
│   ├── Clustering (DBSCAN, K-Means)
│   └── Streaming processing
│
└── Shared Dependencies
    ├── Qdrant (Port 6333)
    ├── Disk Cache (.diskcache)
    └── Common utilities
```

---

## 📚 **Documentation Structure**

### **Primary Documents**
- **ARCHITECTURE.md** - System architecture and service topology
- **DEVELOPER_ROADMAP.md** - Outstanding tasks and priorities
- **This file (AGENTS.md)** - Agent development guidelines

### **Service-Specific Documentation**
- `ingestion_orchestration_fastapi_app/README.md` - Ingestion pipeline
- `ml_inference_fastapi_app/README.md` - ML inference service
- `gpu_umap_service/README.md` - GPU-accelerated UMAP

### **Cursor Rules** (`.cursor/rules/backend/`)
- `backend-development-index.mdc` - Master index
- `fastapi-microservice-patterns.mdc` - Service architecture
- `fastapi-dependency-injection.mdc` - Preventing circular imports
- `ml-service-integration.mdc` - GPU and ML patterns
- `api-design-patterns.mdc` - REST API design

---

## 🚀 **Getting Started**

### **Step 1: Understand the Service You're Working On**

| Service | When to Work On It |
|---------|-------------------|
| **Ingestion Orchestration** | Collection management, pipeline coordination, thumbnails |
| **ML Inference** | CLIP/BLIP models, embeddings, captions, GPU optimization |
| **GPU-UMAP** | Dimensionality reduction, clustering, streaming processing |

### **Step 2: Follow Service-Specific Patterns**

#### **For Ingestion Orchestration Service**
```bash
# Location
backend/ingestion_orchestration_fastapi_app/

# Key Files
├── main.py                 # Lifespan, app setup
├── dependencies.py         # AppState, dependency providers
├── routers/                # API endpoints
│   ├── collections.py      # Collection CRUD
│   ├── ingest.py           # Ingestion jobs
│   ├── search.py           # Text/image search
│   ├── images.py           # Image serving
│   └── umap.py             # UMAP/clustering
└── pipeline/               # Ingestion pipeline
    ├── manager.py          # Pipeline orchestration
    ├── io_scanner.py       # Directory scanning
    ├── cpu_processor.py    # File processing
    ├── gpu_worker.py       # ML service calls
    └── db_upserter.py      # Qdrant upsertion
```

**Common Tasks:**
- **Add new endpoint**: Create in `routers/`, follow REST patterns
- **Modify pipeline**: Update appropriate pipeline stage
- **Change batch sizes**: Use `utils/autosize.py` pattern
- **Add caching**: Use `diskcache` pattern from `cpu_processor.py`

#### **For ML Inference Service**
```bash
# Location
backend/ml_inference_fastapi_app/

# Key Files
├── main.py                 # Lifespan, app setup
├── routers/
│   └── inference.py        # Embedding/caption endpoints
└── services/
    ├── clip_service.py     # CLIP model management
    ├── blip_service.py     # BLIP model management
    └── redis_scheduler.py  # Job scheduling
```

**Common Tasks:**
- **GPU optimization**: Modify `services/clip_service.py` or `blip_service.py`
- **Batch processing**: Update `routers/inference.py`
- **Model loading**: Change lifespan in `main.py`
- **Memory management**: Check safe batch size calculations

#### **For GPU-UMAP Service**
```bash
# Location
backend/gpu_umap_service/

# Key Files
├── main.py                      # App setup
└── umap_service/
    ├── main.py                  # UMAP endpoints
    └── streaming_service.py     # Streaming processing
```

**Common Tasks:**
- **Add clustering algorithm**: Modify `umap_service/main.py`
- **Improve streaming**: Update `streaming_service.py`
- **GPU optimization**: Check cuML usage patterns

---

## 🔧 **Development Patterns**

### **1. Dependency Injection (CRITICAL)**

✅ **ALWAYS use this pattern** to prevent circular imports:

```python
# dependencies.py
class AppState:
    def __init__(self):
        self.qdrant_client: QdrantClient | None = None
        self.active_collection: str | None = None

app_state = AppState()

def get_qdrant_client() -> QdrantClient:
    if app_state.qdrant_client is None:
        raise RuntimeError("Qdrant client not initialized")
    return app_state.qdrant_client
```

```python
# routers/search.py
from fastapi import APIRouter, Depends
from ..dependencies import get_qdrant_client

router = APIRouter(prefix="/api/v1/search")

@router.post("/")
async def search(
    qdrant_client: QdrantClient = Depends(get_qdrant_client)
):
    # Use qdrant_client here
```

❌ **NEVER import main.py from routers** - causes circular imports

### **2. Async Patterns**

```python
# ✅ Offload CPU-bound work to threads
file_hash = await asyncio.to_thread(compute_sha256, file_path)

# ✅ Use async context managers
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data)

# ❌ NEVER block the event loop
def blocking_work():
    time.sleep(10)  # FORBIDDEN
```

### **3. GPU Resource Management**

```python
# ✅ ALWAYS use GPU lock for exclusive access
import asyncio

gpu_lock = asyncio.Lock()

async def gpu_operation(data):
    async with gpu_lock:
        try:
            result = model(data)
            return result
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()  # MANDATORY
```

### **4. Error Handling**

```python
# ✅ Structured error handling
class ServiceError(Exception):
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}

try:
    result = await process_data(request.data)
    return result
except ServiceError as e:
    raise HTTPException(
        status_code=400 if e.code.startswith("INVALID") else 500,
        detail={"code": e.code, "message": e.message, "details": e.details}
    )
```

### **5. Pydantic Models**

```python
# ✅ Comprehensive validation with Field()
from pydantic import BaseModel, Field
from typing import List, Optional

class ProcessRequest(BaseModel):
    data_path: str = Field(..., min_length=1, description="Path to data")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "data_path": "/path/to/data",
                "options": {"batch_size": 32}
            }
        }
```

---

## 📋 **Common Development Tasks**

### **Adding a New Endpoint**

1. **Choose the right service** (Ingestion, ML, or UMAP)
2. **Create router function** following REST conventions
3. **Define Pydantic models** for request/response
4. **Use dependency injection** for shared resources
5. **Add error handling** with structured exceptions
6. **Update service README** with endpoint documentation
7. **Test with `/docs`** Swagger UI

### **Modifying the Ingestion Pipeline**

The ingestion pipeline has 4 stages:

```
[IO Scanner] → raw_queue → [CPU Processor] → ml_queue → 
[GPU Worker] → db_queue → [DB Upserter]
```

**To modify a stage:**
1. **Identify the stage file** in `pipeline/`
2. **Understand queue flow** - what goes in/out
3. **Maintain queue semantics** - put sentinels (None) for shutdown
4. **Update job context** if adding new tracking metrics
5. **Test with small dataset** before large-scale ingestion

### **Optimizing ML Performance**

**CLIP/BLIP Optimization Checklist:**
- [ ] Use `torch.compile()` for PyTorch 2.0+
- [ ] Enable FP16 (`.half()`) for memory efficiency
- [ ] Probe safe batch sizes based on GPU memory
- [ ] Use `torch.inference_mode()` instead of `torch.no_grad()`
- [ ] Implement OOM recovery with batch splitting
- [ ] Always call `torch.cuda.empty_cache()` after operations

**See:** `.cursor/rules/backend/ml-service-integration.mdc`

### **Working with Qdrant**

```python
# ✅ Batch operations for efficiency
from qdrant_client.http.models import PointStruct

points = [
    PointStruct(
        id=str(uuid.uuid4()),
        vector=embedding,
        payload=metadata
    )
    for embedding, metadata in zip(embeddings, metadata_list)
]

qdrant_client.upsert(
    collection_name=collection_name,
    points=points,
    wait=False  # Async upsert for better performance
)
```

**Best Practices:**
- Use UUIDs for point IDs (not SHA256 hashes)
- Store file hashes in payload for deduplication
- Batch upserts in groups of 32-64
- Use `on_disk=True` for large collections
- Disable HNSW during ingestion, re-enable after

---

## 🐛 **Debugging Guide**

### **Service Won't Start**

1. **Check circular imports**:
```bash
python -c "from backend.ingestion_orchestration_fastapi_app.main import app"
```

2. **Verify dependencies.py exists** and has proper structure

3. **Check environment variables**:
```bash
# Required variables
QDRANT_HOST=localhost
QDRANT_PORT=6333
ML_INFERENCE_SERVICE_URL=http://localhost:8001
```

### **GPU Issues**

```bash
# 1. Verify CUDA
nvidia-smi

# 2. Check PyTorch GPU access
python -c "import torch; print(torch.cuda.is_available())"

# 3. Check memory
python -c "import torch; print(torch.cuda.get_device_properties(0))"
```

### **Pipeline Stalls**

**Symptoms**: Ingestion starts but never completes

**Debugging Steps:**
1. Check queue sizes in logs - are they filling up?
2. Verify ML service is responding - test `/health`
3. Check GPU worker logs for OOM errors
4. Verify Qdrant connection - test with `qdrant.get_collections()`

### **Performance Issues**

```bash
# Profile ingestion pipeline
python backend/scripts/ingest_benchmark.py --folder /path/to/images

# Check ML service capabilities
curl http://localhost:8001/api/v1/capabilities

# Monitor GPU usage
nvidia-smi -l 1
```

---

## ⚠️ **Critical Warnings**

### **Never Do These**

❌ **Import main.py from routers** - Causes circular import hell  
❌ **Block event loop** - Use `asyncio.to_thread()` for CPU work  
❌ **Ignore GPU cleanup** - Always call `torch.cuda.empty_cache()`  
❌ **Skip error handling** - Wrap everything in try/except  
❌ **Use global state without injection** - Use dependencies.py  
❌ **Hardcode batch sizes** - Query service capabilities  

### **Always Do These**

✅ **Use dependency injection** - Follow patterns in dependencies.py  
✅ **Async for I/O** - All database/network calls are async  
✅ **Background tasks** - Use FastAPI BackgroundTasks for long operations  
✅ **Structured logging** - Include context (job_id, service, etc.)  
✅ **Type hints** - All functions have proper types  
✅ **Pydantic validation** - All requests/responses use models  

---

## 📊 **Performance Targets**

### **Ingestion Service**
- **25 images**: < 65 seconds end-to-end
- **Batch processing**: 471 images per GPU batch (safe limit)
- **Cache hit ratio**: > 80% for repeated ingestion
- **Concurrent jobs**: Support multiple collections

### **ML Inference Service**
- **CLIP encoding**: < 40s for 25 images
- **BLIP captioning**: < 15s for 25 images
- **Model loading**: < 30s at startup
- **GPU utilization**: > 50%

### **GPU-UMAP Service**
- **1K points**: < 3 seconds for UMAP projection
- **10K points**: < 15 seconds with streaming
- **Clustering**: < 2 seconds for DBSCAN on 1K points
- **Memory efficient**: Chunked processing for large datasets

---

## 🧪 **Testing Strategy**

### **Unit Tests**
```bash
# Test individual services
pytest backend/ingestion_orchestration_fastapi_app/tests/
pytest backend/ml_inference_fastapi_app/tests/
pytest backend/gpu_umap_service/tests/
```

### **Integration Tests**
```bash
# Test service-to-service communication
pytest tests/integration/test_ingestion_pipeline.py
pytest tests/integration/test_ml_integration.py
```

### **Benchmark Tests**
```bash
# Performance benchmarking
python backend/scripts/ingest_benchmark.py --folder /path/to/test/images
python backend/scripts/benchmark_cuda.py
```

### **API Testing**
```bash
# Test endpoints directly
curl http://localhost:8002/health
curl http://localhost:8001/api/v1/capabilities
curl http://localhost:8003/health

# Use Swagger UI
open http://localhost:8002/docs
open http://localhost:8001/docs
open http://localhost:8003/docs
```

---

## 📖 **Code Style Standards**

### **Python Style**
- Follow PEP 8 style guide
- Use type hints for all functions
- Docstrings for all public functions
- Import order: stdlib, third-party, local

### **FastAPI Conventions**
- Use dependency injection with `Depends()`
- Lifespan context managers for startup/shutdown
- Pydantic models for all request/response
- RESTful URL design with proper HTTP verbs

### **Logging Standards**
```python
# ✅ Structured logging with context
logger.info(
    f"[{job_id}] Processing batch: {len(batch)} items",
    extra={
        "job_id": job_id,
        "batch_size": len(batch),
        "service": "ingestion"
    }
)
```

---

## 🎯 **Success Criteria**

An AI agent is successful when:

✅ **Code Quality**: Matches existing patterns and conventions  
✅ **Performance**: Meets or exceeds benchmark targets  
✅ **Testing**: Adequate test coverage for new features  
✅ **Documentation**: Clear README and docstring updates  
✅ **Integration**: Works seamlessly with other services  
✅ **Error Handling**: Graceful degradation and recovery  

---

## 📞 **Getting Help**

### **Where to Look**

1. **Service README** - Specific implementation details
2. **ARCHITECTURE.md** - System design and data flow
3. **Cursor Rules** - Detailed coding patterns
4. **Code Comments** - Implementation rationale
5. **Swagger /docs** - Interactive API testing

### **Common Issues Solutions**

| Issue | Solution Document |
|-------|------------------|
| Circular imports | `.cursor/rules/backend/fastapi-dependency-injection.mdc` |
| GPU memory errors | `.cursor/rules/backend/ml-service-integration.mdc` |
| Pipeline stalls | `ingestion_orchestration_fastapi_app/README.md` |
| Slow performance | `DEVELOPER_ROADMAP.md` - Optimization section |

---

**Last Updated**: Sprint 11 (September 2025)  
**Version**: 2.0  
**Status**: Production Guidelines

**🚀 Backend Services | ⚡ GPU-Optimized | 🎯 Production-Ready**

