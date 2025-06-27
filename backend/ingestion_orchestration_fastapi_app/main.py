import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
from typing import Dict, Any
from pydantic import BaseModel
import diskcache
from PIL import Image
import asyncio

# Import the global state manager and the routers
from .dependencies import app_state, get_qdrant_client
from .routers import search, images, duplicates, random, collections, umap, curation # and any others

# Configure logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager. This is the recommended way to manage
    startup and shutdown events in modern FastAPI.
    """
    # --- Startup ---
    logger.info("Starting up services...")
    
    # Initialize Qdrant Client
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
    app_state.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
    logger.info(f"Qdrant client initialized for {qdrant_host}:{qdrant_port}")

    # Note: We don't load ML models here anymore - we use the ML service via HTTP
    logger.info("Using ML service at http://localhost:8001 for embeddings")

    # No default active collection - users must explicitly select one
    app_state.active_collection = None
    logger.info("No default collection set. Users must select a collection via the API.")
    
    logger.info("Startup complete.")
    yield
    # --- Shutdown ---
    logger.info("Shutting down services...")
    if app_state.qdrant_client:
        # Qdrant client might have a close() method in some versions
        # app_state.qdrant_client.close()
        pass
    logger.info("Shutdown complete.")


# Create the FastAPI app instance with the lifespan manager
app = FastAPI(
    title="Ingestion Orchestration Service",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routers
# Now, they don't need access to the `app` object anymore.
app.include_router(search.router)
app.include_router(images.router)
app.include_router(duplicates.router)
app.include_router(random.router)
app.include_router(collections.router)
app.include_router(umap.router)
app.include_router(curation.router)

# Import and include the ingest router
from .routers import ingest
app.include_router(ingest.router)

# --- API V1 Router Setup ---
# Define the versioned router BEFORE it is used by decorators
v1_router = APIRouter(prefix="/api/v1", tags=["collections"])

class CollectionNameRequest(BaseModel):
    collection_name: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Vibe Coding API"}

# A simple health check endpoint
@app.get("/health")
async def health():
    # Check Qdrant connection with retries to handle startup races
    max_retries = 5
    retry_delay_seconds = 2
    for attempt in range(max_retries):
        try:
            # This is the operation that might fail during startup
            app_state.qdrant_client.get_collections()
            qdrant_status = "ok"
            break  # Success, exit the loop
        except Exception as e:
            logger.warning(f"Health check attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay_seconds)
            else:
                qdrant_status = "error"
    
    # We don't check ML model here anymore since we use the ML service
    
    if qdrant_status == "ok":
        return {"status": "ok", "services": {"qdrant": qdrant_status, "ml_service": "external"}}
    else:
        raise HTTPException(status_code=503, detail={"status": "error", "services": {"qdrant": qdrant_status, "ml_service": "external"}})


# Example endpoint to change the active collection
# @app.post("/api/v1/collections/select", tags=["collections"])
# def select_collection(collection_name: str):
#     """
#     An endpoint to change the globally active collection.
#     """
#     logger.info(f"Changing active collection from '{app_state.active_collection}' to '{collection_name}'")
#     app_state.active_collection = collection_name
#     return {"message": f"Active collection changed to '{collection_name}'"}

# Legacy collection routes were replaced by `routers/collections.py` to avoid duplication and validation issues.

# --- Legacy image endpoints removed ---
# Image serving is now handled by the images router in routers/images.py

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
