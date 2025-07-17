import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import numpy as np
from sklearn.metrics import silhouette_score
import time

try:
    from cuml.manifold import UMAP
    from cuml.cluster import DBSCAN as cuDBSCAN, HDBSCAN as cuHDBSCAN, KMeans as cuKMeans
    CUDA_AVAILABLE = True
except Exception:
    from umap import UMAP
    from sklearn.cluster import DBSCAN as cuDBSCAN, KMeans as cuKMeans
    try:
        from hdbscan import HDBSCAN as cuHDBSCAN
    except Exception:
        cuHDBSCAN = None
    CUDA_AVAILABLE = False

from .streaming_service import streaming_service, ProcessingStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# === EXISTING MODELS ===
class FitTransformRequest(BaseModel):
    data: List[List[float]]

class TransformRequest(BaseModel):
    data: List[List[float]]

class ClusterRequest(BaseModel):
    data: List[List[float]]
    algorithm: str = "dbscan"
    n_clusters: Optional[int] = None
    eps: Optional[float] = None
    min_samples: Optional[int] = None
    min_cluster_size: Optional[int] = None

# === NEW STREAMING MODELS ===
class StreamingUMAPRequest(BaseModel):
    data: List[List[float]]
    n_components: int = Field(2, ge=1, le=10)
    n_neighbors: int = Field(15, ge=2, le=100)
    min_dist: float = Field(0.1, ge=0.0, le=1.0)
    metric: str = Field("cosine", description="Distance metric for UMAP")
    random_state: int = Field(42, description="Random seed for reproducibility")

class StreamingClusterRequest(BaseModel):
    data: List[List[float]]
    algorithm: str = Field("dbscan", description="Clustering algorithm")
    n_clusters: Optional[int] = Field(None, ge=1, le=1000)
    eps: Optional[float] = Field(None, ge=0.0, le=10.0)
    min_samples: Optional[int] = Field(None, ge=1, le=100)
    min_cluster_size: Optional[int] = Field(None, ge=1, le=1000)

class JobStatusResponse(BaseModel):
    job_id: str
    status: ProcessingStatus
    total_points: int
    processed_points: int
    current_chunk: int
    total_chunks: int
    progress_percentage: float
    estimated_completion: Optional[float] = None
    processing_time: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class JobStartResponse(BaseModel):
    job_id: str
    status: str
    message: str
    total_points: int
    estimated_chunks: int

# === EXISTING ENDPOINTS (KEPT FOR BACKWARD COMPATIBILITY) ===
model = None

@router.post("/fit_transform")
async def fit_transform(req: FitTransformRequest):
    data = np.array(req.data, dtype=np.float32)
    if data.ndim != 2:
        raise HTTPException(status_code=422, detail="Data must be 2D")
    try:
        reducer = UMAP(n_components=2)
        embedding = reducer.fit_transform(data)
        global model
        model = reducer
        return embedding.tolist()
    except Exception as e:
        logger.exception("UMAP fit_transform failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transform")
async def transform(req: TransformRequest):
    if model is None:
        raise HTTPException(status_code=400, detail="Model not fitted")
    data = np.array(req.data, dtype=np.float32)
    if data.ndim != 2:
        raise HTTPException(status_code=422, detail="Data must be 2D")
    try:
        embedding = model.transform(data)
        return embedding.tolist()
    except Exception as e:
        logger.exception("UMAP transform failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cluster")
async def cluster(req: ClusterRequest):
    data = np.array(req.data, dtype=np.float32)
    if data.ndim != 2:
        raise HTTPException(status_code=422, detail="Data must be 2D")

    algo = req.algorithm.lower()
    try:
        if algo == "dbscan":
            eps = req.eps
            if eps is None:
                from sklearn.neighbors import NearestNeighbors
                k = min(5, len(data) - 1)
                nbrs = NearestNeighbors(n_neighbors=k + 1).fit(data)
                dists, _ = nbrs.kneighbors(data)
                eps = float(np.median(dists[:, k]))
            min_samples = req.min_samples or 5
            clusterer = cuDBSCAN(eps=eps, min_samples=min_samples)
        elif algo == "hdbscan":
            if cuHDBSCAN is None:
                raise HTTPException(status_code=500, detail="HDBSCAN not available")
            min_cluster_size = req.min_cluster_size or 5
            clusterer = cuHDBSCAN(min_cluster_size=min_cluster_size)
        elif algo == "kmeans":
            n_clusters = req.n_clusters or 8
            clusterer = cuKMeans(n_clusters=n_clusters)
        elif algo == "hierarchical":
            from sklearn.cluster import AgglomerativeClustering
            n_clusters = req.n_clusters or 8
            clusterer = AgglomerativeClustering(n_clusters=n_clusters)
        else:
            raise HTTPException(status_code=400, detail="Unsupported algorithm")

        labels = clusterer.fit_predict(data)

        # cuML may return cudf.Series or cupy array; convert safely
        try:
            if hasattr(labels, 'to_numpy'):
                labels = labels.to_numpy()
            elif 'cupy' in str(type(labels)):
                import cupy as cp
                labels = cp.asnumpy(labels)
        except Exception:
            pass  # Fallback to original labels if conversion fails

        labels = labels.astype(int)

        # === Compute per-cluster metadata (size, centroid, convex hull) ===
        from collections import defaultdict
        cluster_stats = defaultdict(lambda: {
            "points": [],
        })
        for pt, lbl in zip(data.tolist(), labels):
            cluster_stats[int(lbl)]["points"].append(pt)

        # Build summary structures
        clusters_summary = {}
        from shapely.geometry import MultiPoint
        for cid, info in cluster_stats.items():
            pts = np.array(info["points"], dtype=np.float32)
            centroid = pts.mean(axis=0).tolist()
            hull_coords = None
            if len(pts) >= 3:
                try:
                    hull = MultiPoint(pts).convex_hull
                    hull_coords = list(map(list, hull.exterior.coords)) if hull and hasattr(hull, "exterior") else None
                except Exception:
                    hull_coords = None
            clusters_summary[cid] = {
                "size": len(pts),
                "centroid": centroid,
                "hull": hull_coords,
            }

        score = None
        unique_labels = set(labels)
        if len(unique_labels) > 1 and not (-1 in unique_labels and len(unique_labels) == 2):
            score = float(silhouette_score(data, labels))

        return {
            "labels": labels.tolist(),
            "silhouette_score": score,
            "clusters": clusters_summary,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Clustering failed")
        raise HTTPException(status_code=500, detail=str(e))

# === NEW STREAMING ENDPOINTS ===

@router.post("/streaming/umap", response_model=JobStartResponse)
async def start_streaming_umap(req: StreamingUMAPRequest):
    """Start streaming UMAP processing for large datasets."""
    try:
        if len(req.data) == 0:
            raise HTTPException(status_code=422, detail="Data cannot be empty")
        
        # Determine if we should use streaming based on dataset size
        if len(req.data) < 1000:
            # For small datasets, use the traditional approach
            logger.info(f"Small dataset ({len(req.data)} points), using traditional UMAP")
            reducer = UMAP(
                n_components=req.n_components,
                n_neighbors=req.n_neighbors,
                min_dist=req.min_dist,
                metric=req.metric,
                random_state=req.random_state
            )
            data_array = np.array(req.data, dtype=np.float32)
            embeddings = reducer.fit_transform(data_array)
            
            return JobStartResponse(
                job_id="immediate",
                status="completed",
                message="Small dataset processed immediately",
                total_points=len(req.data),
                estimated_chunks=1
            )
        
        # For large datasets, use streaming
        job_id = await streaming_service.start_streaming_umap(
            data=req.data,
            n_components=req.n_components,
            n_neighbors=req.n_neighbors,
            min_dist=req.min_dist,
            metric=req.metric,
            random_state=req.random_state
        )
        
        total_chunks = (len(req.data) + streaming_service.chunk_size - 1) // streaming_service.chunk_size
        
        return JobStartResponse(
            job_id=job_id,
            status="started",
            message=f"Streaming UMAP processing started for {len(req.data)} points",
            total_points=len(req.data),
            estimated_chunks=total_chunks
        )
        
    except Exception as e:
        logger.exception("Failed to start streaming UMAP")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/streaming/cluster", response_model=JobStartResponse)
async def start_streaming_clustering(req: StreamingClusterRequest):
    """Start streaming clustering for large datasets."""
    try:
        if len(req.data) == 0:
            raise HTTPException(status_code=422, detail="Data cannot be empty")
        
        # Determine if we should use streaming based on dataset size
        if len(req.data) < 1000:
            # For small datasets, use the traditional approach
            logger.info(f"Small dataset ({len(req.data)} points), using traditional clustering")
            data_array = np.array(req.data, dtype=np.float32)
            
            # Use existing clustering logic
            algo = req.algorithm.lower()
            if algo == "dbscan":
                eps = req.eps
                if eps is None:
                    from sklearn.neighbors import NearestNeighbors
                    k = min(5, len(data_array) - 1)
                    nbrs = NearestNeighbors(n_neighbors=k + 1).fit(data_array)
                    dists, _ = nbrs.kneighbors(data_array)
                    eps = float(np.median(dists[:, k]))
                min_samples = req.min_samples or 5
                clusterer = cuDBSCAN(eps=eps, min_samples=min_samples)
            elif algo == "hdbscan":
                if cuHDBSCAN is None:
                    raise HTTPException(status_code=500, detail="HDBSCAN not available")
                min_cluster_size = req.min_cluster_size or 5
                clusterer = cuHDBSCAN(min_cluster_size=min_cluster_size)
            elif algo == "kmeans":
                n_clusters = req.n_clusters or 8
                clusterer = cuKMeans(n_clusters=n_clusters)
            elif algo == "hierarchical":
                from sklearn.cluster import AgglomerativeClustering
                n_clusters = req.n_clusters or 8
                clusterer = AgglomerativeClustering(n_clusters=n_clusters)
            else:
                raise HTTPException(status_code=400, detail="Unsupported algorithm")
            
            labels = clusterer.fit_predict(data_array)
            
            return JobStartResponse(
                job_id="immediate",
                status="completed",
                message="Small dataset processed immediately",
                total_points=len(req.data),
                estimated_chunks=1
            )
        
        # For large datasets, use streaming
        job_id = await streaming_service.start_streaming_clustering(
            data=req.data,
            algorithm=req.algorithm,
            n_clusters=req.n_clusters,
            eps=req.eps,
            min_samples=req.min_samples,
            min_cluster_size=req.min_cluster_size
        )
        
        total_chunks = (len(req.data) + streaming_service.chunk_size - 1) // streaming_service.chunk_size
        
        return JobStartResponse(
            job_id=job_id,
            status="started",
            message=f"Streaming clustering started for {len(req.data)} points",
            total_points=len(req.data),
            estimated_chunks=total_chunks
        )
        
    except Exception as e:
        logger.exception("Failed to start streaming clustering")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/streaming/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the status of a streaming job."""
    if job_id == "immediate":
        # Handle immediate completion for small datasets
        return JobStatusResponse(
            job_id=job_id,
            status=ProcessingStatus.COMPLETED,
            total_points=0,
            processed_points=0,
            current_chunk=1,
            total_chunks=1,
            progress_percentage=100.0,
            processing_time=0.0
        )
    
    job = streaming_service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    progress_percentage = (job.processed_points / job.total_points) * 100 if job.total_points > 0 else 0
    processing_time = time.time() - job.start_time
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        total_points=job.total_points,
        processed_points=job.processed_points,
        current_chunk=job.current_chunk,
        total_chunks=job.total_chunks,
        progress_percentage=progress_percentage,
        estimated_completion=job.estimated_completion,
        processing_time=processing_time,
        result=job.result,
        error=job.error
    )

@router.delete("/streaming/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a streaming job."""
    if job_id == "immediate":
        return {"message": "Immediate jobs cannot be cancelled"}
    
    success = streaming_service.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": f"Job {job_id} cancelled successfully"}

@router.get("/streaming/jobs")
async def list_active_jobs():
    """List all active streaming jobs."""
    active_jobs = []
    for job_id, job in streaming_service.active_jobs.items():
        progress_percentage = (job.processed_points / job.total_points) * 100 if job.total_points > 0 else 0
        processing_time = time.time() - job.start_time
        
        active_jobs.append({
            "job_id": job_id,
            "status": job.status,
            "total_points": job.total_points,
            "processed_points": job.processed_points,
            "progress_percentage": progress_percentage,
            "processing_time": processing_time,
            "start_time": job.start_time
        })
    
    return {
        "active_jobs": active_jobs,
        "total_jobs": len(active_jobs)
    }

# === BACKGROUND TASK FOR CLEANUP ===
@router.post("/streaming/cleanup")
async def cleanup_old_jobs(background_tasks: BackgroundTasks):
    """Clean up old completed jobs to prevent memory leaks."""
    background_tasks.add_task(streaming_service.cleanup_completed_jobs)
    return {"message": "Cleanup task scheduled"}
