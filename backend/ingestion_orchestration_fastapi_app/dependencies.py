from fastapi import HTTPException, Request
from qdrant_client import QdrantClient

def get_qdrant_dependency(request: Request) -> QdrantClient:
    q_client = request.app.state.qdrant_client
    if q_client is None:
        raise HTTPException(status_code=503, detail="Qdrant service not available - client not initialized.")
    return q_client 