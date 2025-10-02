# ML Inference Service - Agent Guidelines

## 🎯 **Service Purpose**

The ML Inference Service hosts AI models (CLIP, BLIP) for generating image embeddings and captions. It provides GPU-accelerated inference with dynamic batch sizing.

**Port**: 8001  
**Technology**: FastAPI, PyTorch, Transformers  
**Models**: OpenAI CLIP (ViT-B/32), Salesforce BLIP

---

## 🏗️ **Service Architecture**

### **Core Components**

```
ML Inference Service
├── main.py                  # Lifespan, app setup
├── routers/
│   └── inference.py         # API endpoints
└── services/
    ├── clip_service.py      # CLIP model + GPU lock
    ├── blip_service.py      # BLIP model
    └── redis_scheduler.py   # Job scheduling
```

### **GPU Resource Management**

```python
# Shared GPU lock across services
gpu_lock = asyncio.Lock()

# Always use lock for GPU operations
async with gpu_lock:
    embeddings = model(batch_tensor)
    torch.cuda.empty_cache()  # CRITICAL
```

---

## 🔧 **Common Development Tasks**

### **Modifying Model Loading**

Models are loaded in the lifespan context manager:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with clip_service.gpu_lock:
        await clip_service.load_clip_model()
        clip_service.recalculate_safe_batch_size()
        
        await blip_service.load_blip_model()
        blip_service.recalculate_safe_batch_size()
    
    yield
    
    # Shutdown
    async with clip_service.gpu_lock:
        await clip_service.cooldown_clip_model()
        await blip_service.cooldown_blip_model()
```

**To change model:**
```bash
export CLIP_MODEL="openai/clip-vit-large-patch14"
export BLIP_MODEL="Salesforce/blip-image-captioning-large"
```

### **Adding New Inference Endpoint**

```python
# In routers/inference.py
from fastapi import APIRouter
from ..services import clip_service

@router.post("/my_new_endpoint")
async def my_inference_endpoint(request: MyRequest):
    # Check model is loaded
    if not clip_service.get_clip_model_status():
        raise HTTPException(status_code=503, detail="Model not ready")
    
    # Perform inference with GPU lock (already in service)
    result = clip_service.encode_image_batch(images)
    
    return {"result": result}
```

### **Optimizing Batch Processing**

**Current Pattern** (handles OOM gracefully):

```python
def encode_image_batch(images: list[Any]) -> torch.Tensor:
    try:
        inputs = CLIP_PROCESSOR(images=images, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            features = CLIP_MODEL.get_image_features(**inputs)
        return features
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            # Split batch and retry
            torch.cuda.empty_cache()
            if len(images) == 1:
                raise  # Can't split further
            mid = len(images) // 2
            left = encode_image_batch(images[:mid])
            right = encode_image_batch(images[mid:])
            return torch.cat([left, right], dim=0)
        raise
```

---

## 📊 **Key Patterns**

### **1. Safe Batch Size Calculation**

```python
def recalculate_safe_batch_size():
    """Probe GPU memory and determine safe batch size."""
    if DEVICE.type != "cuda":
        SAFE_CLIP_BATCH_SIZE = 1
        return
    
    # Create dummy input
    dummy_image = torch.zeros((3, 224, 224), device=DEVICE)
    
    # Measure memory usage
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(DEVICE)
    
    baseline = torch.cuda.memory_allocated(DEVICE)
    encode_image_batch([dummy_image])
    peak = torch.cuda.max_memory_allocated(DEVICE)
    
    torch.cuda.empty_cache()
    
    # Calculate safe batch size
    mem_per_item = peak - baseline
    free_mem, _ = torch.cuda.mem_get_info(DEVICE)
    
    safe_size = int((free_mem * 0.8) / mem_per_item)
    SAFE_CLIP_BATCH_SIZE = max(1, safe_size)
```

### **2. Model Optimization**

```python
async def load_clip_model():
    model = AutoModel.from_pretrained(CLIP_MODEL_NAME)
    
    if DEVICE.type == 'cuda':
        # Use FP16 for memory efficiency
        model.to(torch.float16)
        
        # Apply torch.compile for performance (PyTorch 2.0+)
        try:
            model = torch.compile(model, mode="reduce-overhead")
            logger.info("✅ torch.compile optimization applied")
        except Exception as e:
            logger.warning(f"torch.compile failed: {e}")
    
    model = model.to(DEVICE)
    model.eval()
    return model
```

### **3. Parallel Preprocessing**

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

cpu_executor = ThreadPoolExecutor(max_workers=os.cpu_count())

async def preprocess_batch_parallel(batch_items):
    """Preprocess images in parallel before GPU inference."""
    tasks = [
        asyncio.to_thread(preprocess_image, item.image_data)
        for item in batch_items
    ]
    return await asyncio.gather(*tasks)
```

---

## 🐛 **Debugging Guide**

### **Model Won't Load**

**Symptoms**: Service fails at startup with model loading errors

**Solutions**:
```bash
# 1. Check model cache
ls ~/.cache/huggingface/hub/

# 2. Clear corrupted cache
rm -rf ~/.cache/huggingface/hub/models--*

# 3. Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"

# 4. Check disk space
df -h ~/.cache/huggingface/
```

### **GPU Out of Memory**

**Symptoms**: CUDA OOM errors during inference

**Solutions**:
1. **Reduce batch size** - Modify safe batch calculation
2. **Clear cache** - Ensure `torch.cuda.empty_cache()` is called
3. **Check other processes** - `nvidia-smi` to see GPU usage
4. **Use FP16** - Ensure models are using `.half()`

### **Slow Inference**

**Debug Steps**:
1. **Check batch size**: Too small = GPU underutilized
2. **Profile GPU usage**: `nvidia-smi -l 1`
3. **Verify torch.compile**: Should see log message at startup
4. **Check preprocessing**: Parallel preprocessing enabled?

---

## ⚠️ **Critical Warnings**

### **Never Do**

❌ **Load models without GPU lock** - Race conditions  
❌ **Skip `torch.cuda.empty_cache()`** - Memory leaks  
❌ **Use synchronous preprocessing** - Blocks event loop  
❌ **Ignore OOM errors** - Implement batch splitting  
❌ **Hardcode batch sizes** - Use capability probing  

### **Always Do**

✅ **Use async with gpu_lock** - Exclusive GPU access  
✅ **Call empty_cache()** - After every GPU operation  
✅ **Offload preprocessing** - Use thread pool  
✅ **Probe capabilities** - Dynamic batch sizing  
✅ **Handle OOM gracefully** - Recursive batch splitting  

---

## 📈 **Performance Targets**

- **Model Loading**: < 30 seconds at startup
- **CLIP Batch (25 images)**: < 40 seconds
- **BLIP Batch (25 images)**: < 15 seconds
- **Safe Batch Size**: > 400 on consumer GPUs
- **GPU Utilization**: > 50% during inference
- **Memory Efficiency**: < 80% VRAM usage at peak

---

## 🧪 **Testing**

```bash
# Unit tests
pytest backend/ml_inference_fastapi_app/tests/

# Benchmark
python backend/scripts/benchmark.py --folder /path/to/images

# API testing
curl -X POST http://localhost:8001/api/v1/warmup
curl http://localhost:8001/api/v1/capabilities
```

---

**Last Updated**: Sprint 11  
**Status**: Production Ready  
**Maintainer**: ML Team

