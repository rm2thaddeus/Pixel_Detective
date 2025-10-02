# GPU-UMAP Service - Agent Guidelines

## 🎯 **Service Purpose**

The GPU-UMAP Service provides CUDA-accelerated dimensionality reduction and clustering using RAPIDS cuML. It handles both small datasets (immediate processing) and large datasets (streaming with progress updates).

**Port**: 8003  
**Technology**: FastAPI, RAPIDS cuML, UMAP, scikit-learn  
**Deployment**: Docker with GPU support

---

## 🏗️ **Service Architecture**

### **Dual Processing Modes**

```
Small Datasets (<1000 points)
  → Immediate processing
  → Return results immediately
  → job_id = "immediate"

Large Datasets (≥1000 points)
  → Streaming processing
  → Background job with UUID
  → Real-time progress updates
  → Chunked processing
```

### **Key Components**

| Component | File | Responsibility |
|-----------|------|---------------|
| **Main Router** | `umap_service/main.py` | API endpoints |
| **Streaming Service** | `umap_service/streaming_service.py` | Background job processing |
| **App Entry** | `main.py` | FastAPI app setup |

---

## 🔧 **Common Development Tasks**

### **Adding a New Clustering Algorithm**

```python
# In umap_service/main.py
def _create_clusterer(algorithm: str, params: dict):
    if algorithm == "my_new_algo":
        from sklearn.cluster import MyNewAlgorithm
        return MyNewAlgorithm(
            param1=params.get('param1', default_value),
            param2=params.get('param2', default_value)
        )
    # ... existing algorithms
```

### **Modifying Streaming Parameters**

```python
# In umap_service/streaming_service.py
streaming_service = StreamingUMAPService(
    chunk_size=1000,           # Points per chunk
    max_concurrent_jobs=3      # Simultaneous jobs
)
```

### **Adjusting Performance Thresholds**

```python
# In umap_service/main.py - Line ~212
IMMEDIATE_THRESHOLD = 1000  # Points

if len(req.data) < IMMEDIATE_THRESHOLD:
    # Use immediate processing
else:
    # Use streaming
```

---

## 📊 **Key Patterns**

### **1. cuML Fallback Pattern**

```python
try:
    from cuml.manifold import UMAP
    from cuml.cluster import DBSCAN, KMeans
    CUDA_AVAILABLE = True
except Exception:
    from umap import UMAP
    from sklearn.cluster import DBSCAN, KMeans
    CUDA_AVAILABLE = False
```

**Auto-detects** GPU availability and falls back gracefully.

### **2. Streaming Job Pattern**

```python
class ProcessingJob:
    job_id: str
    status: ProcessingStatus
    total_points: int
    processed_points: int
    current_chunk: int
    total_chunks: int
    start_time: float
    estimated_completion: Optional[float]
    result: Optional[Dict[str, Any]]
    error: Optional[str]

# Process in chunks with progress updates
for chunk_start in range(0, len(data), chunk_size):
    chunk_data = data[chunk_start:chunk_end]
    
    # Process chunk
    async with gpu_lock:
        chunk_result = process_chunk(chunk_data)
    
    # Update progress
    job.processed_points = chunk_end
    job.current_chunk += 1
    
    # Calculate ETA
    elapsed = time.time() - job.start_time
    progress = job.processed_points / job.total_points
    estimated_total = elapsed / progress
    job.estimated_completion = time.time() + (estimated_total - elapsed)
```

### **3. Cluster Statistics Calculation**

```python
async def _compute_cluster_stats(data: np.ndarray, labels: np.ndarray):
    """Compute cluster statistics efficiently."""
    from collections import defaultdict
    from shapely.geometry import MultiPoint
    
    cluster_stats = defaultdict(lambda: {"points": []})
    
    # Group points by cluster
    for pt, lbl in zip(data.tolist(), labels):
        cluster_stats[int(lbl)]["points"].append(pt)
    
    # Compute per-cluster metrics
    clusters_summary = {}
    for cid, info in cluster_stats.items():
        pts = np.array(info["points"])
        centroid = pts.mean(axis=0).tolist()
        
        # Convex hull for visualization
        hull_coords = None
        if len(pts) >= 3:
            try:
                hull = MultiPoint(pts).convex_hull
                hull_coords = list(map(list, hull.exterior.coords))
            except:
                pass
        
        clusters_summary[cid] = {
            "size": len(pts),
            "centroid": centroid,
            "hull": hull_coords
        }
    
    return clusters_summary
```

---

## 🐛 **Debugging Guide**

### **cuML Not Available**

**Symptoms**: Service falls back to CPU-only UMAP

**Solutions**:
```bash
# 1. Check Docker build
docker build -t gpu-umap-service .

# 2. Verify base image
FROM rapidsai/base:24.08-cuda12.2-py3.11

# 3. Check CUDA in container
docker run --gpus all gpu-umap-service python -c "import cuml; print(cuml.__version__)"
```

### **Streaming Jobs Stuck**

**Symptoms**: Jobs remain in "processing" status indefinitely

**Debug Steps**:
1. **Check job status**:
```bash
curl http://localhost:8003/umap/streaming/jobs
```

2. **Check logs for errors**:
```bash
docker logs <container_id> | grep ERROR
```

3. **Verify GPU lock** isn't deadlocked:
```python
# In streaming_service.py
logger.info(f"Acquiring GPU lock for job {job_id}")
async with gpu_lock:
    logger.info(f"GPU lock acquired for job {job_id}")
    # Processing
logger.info(f"GPU lock released for job {job_id}")
```

### **Performance Degradation**

**Symptoms**: Processing slower than expected

**Solutions**:
1. **Check concurrent jobs**: Too many jobs = resource contention
2. **Verify chunk size**: Too small = overhead, too large = memory issues
3. **Monitor GPU**: `nvidia-smi -l 1`
4. **Check cuML vs sklearn**: Should see "CUDA acceleration" in logs

---

## ⚠️ **Critical Warnings**

### **Never Do**

❌ **Process large datasets synchronously** - Use streaming  
❌ **Skip GPU lock** - Concurrent GPU access = crashes  
❌ **Ignore job cleanup** - Memory leaks from old jobs  
❌ **Return raw cuML objects** - Convert to numpy/lists  
❌ **Block on UMAP fit** - Use async patterns  

### **Always Do**

✅ **Use streaming for >1000 points** - Better UX  
✅ **Acquire GPU lock** - Exclusive access  
✅ **Convert cuML outputs** - To numpy arrays  
✅ **Calculate cluster stats** - Centroids, hulls, sizes  
✅ **Clean up old jobs** - Prevent memory leaks  

---

## 📈 **Performance Targets**

### **UMAP Performance**
- **1K points**: < 3 seconds
- **5K points**: < 10 seconds (streaming)
- **10K points**: < 20 seconds (streaming)
- **Speedup**: 10-300× over CPU

### **Clustering Performance**
- **DBSCAN (1K points)**: < 2 seconds
- **K-Means (1K points)**: < 1 second
- **HDBSCAN (1K points)**: < 3 seconds
- **Hierarchical (1K points)**: < 5 seconds

### **System Performance**
- **Concurrent jobs**: Up to 3 simultaneous
- **Memory usage**: < 500MB per job
- **Job cleanup**: Remove after 24 hours
- **Progress updates**: Every chunk (1K points)

---

## 🧪 **Testing**

```bash
# Test streaming functionality
python test_streaming.py

# Test small dataset
curl -X POST http://localhost:8003/umap/streaming/umap \
  -H "Content-Type: application/json" \
  -d '{"data": [[0.1,0.2],[0.3,0.4]], "n_components": 2}'

# Test large dataset
python -c "
import requests, numpy as np
data = np.random.rand(5000, 512).tolist()
response = requests.post('http://localhost:8003/umap/streaming/umap',
                        json={'data': data, 'n_components': 2})
print(response.json())
"

# Monitor active jobs
curl http://localhost:8003/umap/streaming/jobs
```

---

## 🐳 **Docker Development**

### **Live Reload Setup**

```bash
# Start with live reload
docker compose -f docker-compose.dev.yml up --build

# Rebuild after dependency changes
docker compose -f docker-compose.dev.yml up --build --force-recreate
```

### **GPU Access Verification**

```bash
# Check GPU is accessible in container
docker run --rm --gpus all rapidsai/base:24.08-cuda12.2-py3.11 \
  python -c "import cuml; print('cuML available')"
```

---

**Last Updated**: Sprint 11  
**Status**: Production Ready  
**Maintainer**: UMAP Team

