from fastapi import Request, HTTPException
from qdrant_client import QdrantClient
import os

from .pipeline.manager import PipelineManager
from .config import get_settings

# Environment variables for Qdrant connection
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))

# This is a simple container for our shared resources.
# It's a plain class, so it's easy to understand and doesn't hide any magic.
class AppState:
    def __init__(self):
        self.qdrant_client: Union[QdrantClient, None] = None
        # ML model is no longer managed here - we use the ML service via HTTP
        self.active_collection: Union[str, None] = None
        self.ml_service_url: str = "http://localhost:8001"
        self.is_ready_for_ingestion: bool = False

# We create a single, global instance of this state.
# This is better than attaching to the FastAPI 'app.state' object because
# it's explicitly typed and can be imported safely without circular dependencies.
app_state = AppState()

# --- Dependency Provider Functions ---

def get_qdrant_client() -> QdrantClient:
    """
    Dependency function to get the initialized Qdrant client.
    Raises an exception if the client is not available, ensuring
    that our endpoints fail fast if setup was unsuccessful.
    """
    if app_state.qdrant_client is None:
        raise RuntimeError("Qdrant client has not been initialized.")
    return app_state.qdrant_client

def get_active_collection() -> str:
    """
    Dependency function to get the currently active collection name.
    Raises HTTPException if no collection is selected.
    """
    if app_state.active_collection is None:
        raise HTTPException(status_code=400, detail="No collection selected. Please select a collection first using POST /api/v1/collections/select")
    return app_state.active_collection 