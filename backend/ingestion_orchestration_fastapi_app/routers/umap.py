from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Dict, Any, Optional
from ..dependencies import get_qdrant_client, get_active_collection
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue
import numpy as np
import umap
from sklearn.cluster import DBSCAN, KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from pydantic import BaseModel, Field

router = APIRouter(prefix="/umap", tags=["umap"])

class ClusteringRequest(BaseModel):
    algorithm: str = Field("dbscan", description="Clustering algorithm: dbscan, kmeans, hierarchical")
    n_clusters: Optional[int] = Field(None, description="Number of clusters for kmeans/hierarchical")
    eps: float = Field(0.5, description="DBSCAN eps parameter")
    min_samples: int = Field(5, description="DBSCAN min_samples parameter")

class ClusterLabelRequest(BaseModel):
    cluster_id: int
    label: str

class UMAPProjectionResponse(BaseModel):
    points: List[Dict[str, Any]]
    collection: str
    clustering_info: Optional[Dict[str, Any]] = None

@router.get("/projection", response_model=UMAPProjectionResponse, summary="Get 2-D UMAP projection for a sample of points")
async def umap_projection(
    sample_size: int = Query(500, ge=10, le=5000, description="Number of points to project"),
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection),
):
    """Return a 2-D UMAP projection of CLIP embeddings for quick scatter-plot visualisation.

    The endpoint randomly samples up to *sample_size* points from the active collection,
    runs UMAP (n_components=2, metric='cosine') on their vectors, and returns a list of
    objects: `{id, x, y, thumbnail_base64}`.  This allows the frontend to render an
    interactive 2-D layout.
    """
    try:
        # 1. Sample points (random seed fixed for determinism per call)
        search_result = qdrant.scroll(
            collection_name=collection_name,
            with_vectors=True,
            with_payload=True,
            limit=sample_size,
        )
        points, _ = search_result
        if not points:
            raise HTTPException(status_code=404, detail="Collection is empty")

        ids = [p.id for p in points]
        vectors = np.vstack([p.vector for p in points]).astype(np.float32)

        # 2. Run UMAP on the embeddings
        reducer = umap.UMAP(n_components=2, metric="cosine", random_state=42)
        embedding_2d = reducer.fit_transform(vectors)

        # 3. Build response objects
        results: List[Dict[str, Any]] = []
        for idx, p in enumerate(points):
            payload = p.payload or {}
            results.append({
                "id": ids[idx],
                "x": float(embedding_2d[idx, 0]),
                "y": float(embedding_2d[idx, 1]),
                "thumbnail_base64": payload.get("thumbnail_base64"),
                "filename": payload.get("filename")
            })

        return UMAPProjectionResponse(
            points=results, 
            collection=collection_name
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"UMAP projection failed: {e}")

@router.post("/projection_with_clustering", response_model=UMAPProjectionResponse)
async def umap_projection_with_clustering(
    clustering_config: ClusteringRequest,
    sample_size: int = Query(500, ge=10, le=5000),
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection),
):
    """Generate UMAP projection with automatic clustering using robust algorithms."""
    try:
        # 1. Sample points and get vectors
        search_result = qdrant.scroll(
            collection_name=collection_name,
            with_vectors=True,
            with_payload=True,
            limit=sample_size,
        )
        points, _ = search_result
        if not points:
            raise HTTPException(status_code=404, detail="Collection is empty")

        ids = [p.id for p in points]
        vectors = np.vstack([p.vector for p in points]).astype(np.float32)

        # 2. Run UMAP projection
        reducer = umap.UMAP(n_components=2, metric="cosine", random_state=42)
        embedding_2d = reducer.fit_transform(vectors)

        # 3. Apply clustering algorithm
        cluster_labels, clustering_info = _apply_clustering(
            embedding_2d, vectors, clustering_config
        )

        # 4. Build response with cluster information
        results: List[Dict[str, Any]] = []
        for idx, p in enumerate(points):
            payload = p.payload or {}
            # Update the payload with the new cluster ID. This will be persisted.
            payload["cluster_id"] = int(cluster_labels[idx])
            payload["is_outlier"] = bool(cluster_labels[idx] == -1)
            
            results.append({
                "id": ids[idx],
                "x": float(embedding_2d[idx, 0]),
                "y": float(embedding_2d[idx, 1]),
                "cluster_id": payload["cluster_id"],
                "is_outlier": payload["is_outlier"],
                "thumbnail_base64": payload.get("thumbnail_base64"),
                "filename": payload.get("filename"),
                "caption": payload.get("caption")
            })

        # 5. Persist the updated cluster IDs to Qdrant
        for i, p in enumerate(points):
            qdrant.set_payload(
                collection_name=collection_name,
                payload={
                    "cluster_id": int(cluster_labels[i]),
                    "is_outlier": bool(cluster_labels[i] == -1)
                },
                points=[p.id],
                wait=False # Fire-and-forget for speed
            )

        return UMAPProjectionResponse(
            points=results,
            collection=collection_name,
            clustering_info=clustering_info
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"UMAP clustering failed: {e}")

def _apply_clustering(embedding_2d: np.ndarray, original_vectors: np.ndarray, config: ClusteringRequest):
    """Apply the specified clustering algorithm and return labels and metadata."""
    
    if config.algorithm == "dbscan":
        clusterer = DBSCAN(eps=config.eps, min_samples=config.min_samples)
        cluster_labels = clusterer.fit_predict(embedding_2d)
        
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        n_outliers = list(cluster_labels).count(-1)
        
        clustering_info = {
            "algorithm": "DBSCAN",
            "n_clusters": n_clusters,
            "n_outliers": n_outliers,
            "parameters": {"eps": config.eps, "min_samples": config.min_samples}
        }
        
    elif config.algorithm == "kmeans":
        n_clusters = config.n_clusters or _find_optimal_k(embedding_2d)
        clusterer = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = clusterer.fit_predict(embedding_2d)
        
        # Calculate cluster quality metrics
        silhouette = silhouette_score(embedding_2d, cluster_labels)
        
        clustering_info = {
            "algorithm": "K-Means",
            "n_clusters": n_clusters,
            "silhouette_score": float(silhouette),
            "parameters": {"n_clusters": n_clusters}
        }
        
    elif config.algorithm == "hierarchical":
        n_clusters = config.n_clusters or _find_optimal_k(embedding_2d)
        clusterer = AgglomerativeClustering(n_clusters=n_clusters)
        cluster_labels = clusterer.fit_predict(embedding_2d)
        
        silhouette = silhouette_score(embedding_2d, cluster_labels)
        
        clustering_info = {
            "algorithm": "Hierarchical",
            "n_clusters": n_clusters,
            "silhouette_score": float(silhouette),
            "parameters": {"n_clusters": n_clusters}
        }
        
    else:
        raise ValueError(f"Unsupported clustering algorithm: {config.algorithm}")
    
    return cluster_labels, clustering_info

def _find_optimal_k(data: np.ndarray, max_k: int = 10) -> int:
    """Find optimal number of clusters using silhouette analysis."""
    best_k = 2
    best_score = -1
    
    for k in range(2, min(max_k + 1, len(data))):
        try:
            kmeans = KMeans(n_clusters=k, random_state=42)
            labels = kmeans.fit_predict(data)
            score = silhouette_score(data, labels)
            
            if score > best_score:
                best_score = score
                best_k = k
        except:
            continue
    
    return best_k

@router.post("/cluster_label", status_code=204, summary="Assign a label to a cluster")
async def label_cluster(
    label_request: ClusterLabelRequest,
    collection_name: str = Depends(get_active_collection),
    qdrant: QdrantClient = Depends(get_qdrant_client),
):
    """Assign a persistent 'user_cluster_label' to all points in a given cluster."""
    try:
        qdrant.set_payload(
            collection_name=collection_name,
            payload={"user_cluster_label": label_request.label},
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="cluster_id",
                        match=MatchValue(value=label_request.cluster_id)
                    )
                ]
            ),
            wait=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to label cluster: {e}")
    return

@router.get("/cluster_analysis/{cluster_id}")
async def get_cluster_analysis(
    cluster_id: int,
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
):
    """Get detailed analysis of a specific cluster (placeholder for future enhancement)."""
    # This would be enhanced to provide cluster statistics, representative images, etc.
    return {
        "cluster_id": cluster_id,
        "analysis": "Detailed cluster analysis to be implemented",
        "collection": collection_name
    } 