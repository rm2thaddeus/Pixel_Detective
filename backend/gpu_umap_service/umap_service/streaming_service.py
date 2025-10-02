import asyncio
import logging
import time
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import numpy as np
from fastapi import HTTPException
from pydantic import BaseModel

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

logger = logging.getLogger(__name__)

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ProcessingJob:
    job_id: str
    status: ProcessingStatus
    total_points: int
    processed_points: int
    current_chunk: int
    total_chunks: int
    start_time: float
    estimated_completion: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress_callback: Optional[callable] = None

class StreamingUMAPService:
    """Streaming UMAP service for large datasets with real-time progress."""
    
    def __init__(self, chunk_size: int = 1000, max_concurrent_jobs: int = 3):
        self.chunk_size = chunk_size
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_jobs: Dict[str, ProcessingJob] = {}
        self.job_semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self.gpu_lock = asyncio.Lock() if CUDA_AVAILABLE else None
        
    async def start_streaming_umap(
        self, 
        data: List[List[float]], 
        n_components: int = 2,
        n_neighbors: int = 15,
        min_dist: float = 0.1,
        metric: str = "cosine",
        random_state: int = 42
    ) -> str:
        """Start streaming UMAP processing for large datasets."""
        
        job_id = str(uuid.uuid4())
        total_points = len(data)
        total_chunks = (total_points + self.chunk_size - 1) // self.chunk_size
        
        job = ProcessingJob(
            job_id=job_id,
            status=ProcessingStatus.PENDING,
            total_points=total_points,
            processed_points=0,
            current_chunk=0,
            total_chunks=total_chunks,
            start_time=time.time()
        )
        
        self.active_jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._process_umap_job(job, data, {
            'n_components': n_components,
            'n_neighbors': n_neighbors,
            'min_dist': min_dist,
            'metric': metric,
            'random_state': random_state
        }))
        
        logger.info(f"Started streaming UMAP job {job_id} for {total_points} points in {total_chunks} chunks")
        return job_id
    
    async def _process_umap_job(self, job: ProcessingJob, data: List[List[float]], umap_params: Dict[str, Any]):
        """Process UMAP job in chunks with streaming updates."""
        
        async with self.job_semaphore:
            try:
                job.status = ProcessingStatus.PROCESSING
                job.start_time = time.time()
                
                # Convert data to numpy array
                data_array = np.array(data, dtype=np.float32)
                
                # For UMAP, we need to fit on the entire dataset first, then transform in chunks
                # This is because UMAP needs to see the full dataset structure
                logger.info(f"Job {job.job_id}: Fitting UMAP on full dataset")
                
                async with (self.gpu_lock if self.gpu_lock else asyncio.Lock()):
                    reducer = UMAP(**umap_params)
                    # Fit on the entire dataset
                    reducer.fit(data_array)
                
                # Now transform in chunks for progress updates
                all_embeddings = []
                job.processed_points = 0
                job.current_chunk = 0
                
                for chunk_start in range(0, len(data_array), self.chunk_size):
                    chunk_end = min(chunk_start + self.chunk_size, len(data_array))
                    chunk_data = data_array[chunk_start:chunk_end]
                    
                    # Transform chunk
                    async with (self.gpu_lock if self.gpu_lock else asyncio.Lock()):
                        chunk_embeddings = reducer.transform(chunk_data)
                    
                    # Convert to list and extend results
                    if hasattr(chunk_embeddings, 'tolist'):
                        all_embeddings.extend(chunk_embeddings.tolist())
                    else:
                        all_embeddings.extend(chunk_embeddings)
                    
                    job.processed_points = chunk_end
                    job.current_chunk += 1
                    
                    # Update progress
                    progress = (job.processed_points / job.total_points) * 100
                    logger.info(f"Job {job.job_id}: {progress:.1f}% complete ({job.processed_points}/{job.total_points})")
                    
                    # Estimate completion time
                    elapsed = time.time() - job.start_time
                    if progress > 0:
                        estimated_total = elapsed / (progress / 100)
                        job.estimated_completion = time.time() + (estimated_total - elapsed)
                    
                    # Small delay to prevent overwhelming the system
                    await asyncio.sleep(0.01)
                
                # Job completed successfully
                job.status = ProcessingStatus.COMPLETED
                job.result = {
                    "embeddings": all_embeddings,
                    "total_points": job.total_points,
                    "processing_time": time.time() - job.start_time,
                    "chunks_processed": job.total_chunks
                }
                
                logger.info(f"Job {job.job_id} completed successfully in {job.result['processing_time']:.2f}s")
                
            except Exception as e:
                job.status = ProcessingStatus.FAILED
                job.error = str(e)
                logger.error(f"Job {job.job_id} failed: {e}", exc_info=True)
    
    async def start_streaming_clustering(
        self,
        data: List[List[float]],
        algorithm: str = "dbscan",
        n_clusters: Optional[int] = None,
        eps: Optional[float] = None,
        min_samples: Optional[int] = None,
        min_cluster_size: Optional[int] = None
    ) -> str:
        """Start streaming clustering for large datasets."""
        
        job_id = str(uuid.uuid4())
        total_points = len(data)
        total_chunks = (total_points + self.chunk_size - 1) // self.chunk_size
        
        job = ProcessingJob(
            job_id=job_id,
            status=ProcessingStatus.PENDING,
            total_points=total_points,
            processed_points=0,
            current_chunk=0,
            total_chunks=total_chunks,
            start_time=time.time()
        )
        
        self.active_jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._process_clustering_job(job, data, algorithm, {
            'n_clusters': n_clusters,
            'eps': eps,
            'min_samples': min_samples,
            'min_cluster_size': min_cluster_size,
            'data': data  # Pass data for eps calculation
        }))
        
        logger.info(f"Started streaming clustering job {job_id} for {total_points} points")
        return job_id
    
    async def _process_clustering_job(self, job: ProcessingJob, data: List[List[float]], algorithm: str, params: Dict[str, Any]):
        """Process clustering job with streaming updates."""
        
        async with self.job_semaphore:
            try:
                job.status = ProcessingStatus.PROCESSING
                job.start_time = time.time()
                
                data_array = np.array(data, dtype=np.float32)
                
                # Initialize clustering algorithm
                async with (self.gpu_lock if self.gpu_lock else asyncio.Lock()):
                    clusterer = self._create_clusterer(algorithm, params)
                    labels = clusterer.fit_predict(data_array)
                
                # Convert labels safely
                try:
                    if hasattr(labels, 'to_numpy'):
                        labels = labels.to_numpy()
                    elif 'cupy' in str(type(labels)):
                        import cupy as cp
                        labels = cp.asnumpy(labels)
                except Exception:
                    pass
                
                labels = labels.astype(int)
                
                # Compute cluster statistics
                cluster_stats = await self._compute_cluster_stats(data_array, labels)
                
                # Calculate silhouette score if possible
                score = None
                unique_labels = set(labels)
                if len(unique_labels) > 1 and not (-1 in unique_labels and len(unique_labels) == 2):
                    from sklearn.metrics import silhouette_score
                    score = float(silhouette_score(data_array, labels))
                
                job.status = ProcessingStatus.COMPLETED
                job.result = {
                    "labels": labels.tolist(),
                    "silhouette_score": score,
                    "clusters": cluster_stats,
                    "total_points": job.total_points,
                    "processing_time": time.time() - job.start_time
                }
                
                logger.info(f"Clustering job {job.job_id} completed successfully")
                
            except Exception as e:
                job.status = ProcessingStatus.FAILED
                job.error = str(e)
                logger.error(f"Clustering job {job.job_id} failed: {e}", exc_info=True)
    
    def _create_clusterer(self, algorithm: str, params: Dict[str, Any]):
        """Create clustering algorithm instance."""
        algo = algorithm.lower()
        
        if algo == "dbscan":
            eps = params.get('eps')
            if eps is None:
                from sklearn.neighbors import NearestNeighbors
                data = params.get('data', [])
                k = min(5, len(data) - 1)
                nbrs = NearestNeighbors(n_neighbors=k + 1).fit(data)
                dists, _ = nbrs.kneighbors(data)
                eps = float(np.median(dists[:, k]))
            
            min_samples = params.get('min_samples', 5)
            return cuDBSCAN(eps=eps, min_samples=min_samples)
            
        elif algo == "hdbscan":
            if cuHDBSCAN is None:
                raise HTTPException(status_code=500, detail="HDBSCAN not available")
            min_cluster_size = params.get('min_cluster_size', 5)
            return cuHDBSCAN(min_cluster_size=min_cluster_size)
            
        elif algo == "kmeans":
            n_clusters = params.get('n_clusters', 8)
            return cuKMeans(n_clusters=n_clusters)
            
        elif algo == "hierarchical":
            from sklearn.cluster import AgglomerativeClustering
            n_clusters = params.get('n_clusters', 8)
            return AgglomerativeClustering(n_clusters=n_clusters)
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported algorithm")
    
    async def _compute_cluster_stats(self, data: np.ndarray, labels: np.ndarray) -> Dict[int, Dict[str, Any]]:
        """Compute cluster statistics efficiently."""
        from collections import defaultdict
        
        cluster_stats = defaultdict(lambda: {"points": []})
        
        # Group points by cluster
        for pt, lbl in zip(data.tolist(), labels):
            cluster_stats[int(lbl)]["points"].append(pt)
        
        # Compute statistics for each cluster
        clusters_summary = {}
        for cid, info in cluster_stats.items():
            pts = np.array(info["points"], dtype=np.float32)
            centroid = pts.mean(axis=0).tolist()
            
            # Compute convex hull if enough points
            hull_coords = None
            if len(pts) >= 3:
                try:
                    from shapely.geometry import MultiPoint
                    hull = MultiPoint(pts).convex_hull
                    hull_coords = list(map(list, hull.exterior.coords)) if hull and hasattr(hull, "exterior") else None
                except Exception:
                    hull_coords = None
            
            clusters_summary[cid] = {
                "size": len(pts),
                "centroid": centroid,
                "hull": hull_coords,
            }
        
        return clusters_summary
    
    def get_job_status(self, job_id: str) -> Optional[ProcessingJob]:
        """Get current status of a processing job."""
        return self.active_jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a processing job."""
        if job_id in self.active_jobs:
            self.active_jobs[job_id].status = ProcessingStatus.CANCELLED
            logger.info(f"Job {job_id} cancelled")
            return True
        return False
    
    def cleanup_completed_jobs(self, max_age_hours: int = 24):
        """Clean up old completed jobs to prevent memory leaks."""
        current_time = time.time()
        jobs_to_remove = []
        
        for job_id, job in self.active_jobs.items():
            if job.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
                age_hours = (current_time - job.start_time) / 3600
                if age_hours > max_age_hours:
                    jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
        
        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")

# Global streaming service instance
streaming_service = StreamingUMAPService() 