from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from typing import Union

# This is a simple container for our shared resources.
# It's a plain class, so it's easy to understand and doesn't hide any magic.
class AppState:
    def __init__(self):
        self.qdrant_client: Union[QdrantClient, None] = None
        self.ml_model: Union[SentenceTransformer, None] = None
        self.active_collection: Union[str, None] = None

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

def get_ml_model() -> SentenceTransformer:
    """
    Dependency function to get the initialized ML model.
    """
    if app_state.ml_model is None:
        raise RuntimeError("ML model has not been initialized.")
    return app_state.ml_model

def get_active_collection() -> str:
    """
    Dependency function to get the currently active collection name.
    """
    # In a real app, this might have more logic, but for now,
    # we can depend on the global state.
    if app_state.active_collection is None:
        # You can decide to raise an error or return a default
        # raise HTTPException(status_code=400, detail="No collection selected")
        return "default_collection" # Or whatever your default is
    return app_state.active_collection 