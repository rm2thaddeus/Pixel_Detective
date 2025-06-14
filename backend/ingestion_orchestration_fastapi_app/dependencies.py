from fastapi import HTTPException, Request
from qdrant_client import QdrantClient

def get_qdrant_dependency(request: Request) -> QdrantClient:
    q_client = getattr(request.app.state, 'qdrant_client', None)
    if q_client is None:
        raise HTTPException(status_code=503, detail="Qdrant service not available - client not initialized.")
    return q_client

def get_active_collection(request: Request) -> str:
    """Get the currently active collection name from app state"""
    active_collection = getattr(request.app.state, 'active_collection_name', None)
    if not active_collection:
        raise HTTPException(status_code=400, detail="No collection selected. Please select a collection first.")
    return active_collection 