import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
from sklearn.metrics import silhouette_score

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

router = APIRouter()

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
