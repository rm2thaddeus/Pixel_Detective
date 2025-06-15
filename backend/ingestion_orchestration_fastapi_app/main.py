import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from typing import Dict, Any
from pydantic import BaseModel
import diskcache
from PIL import Image

# Import the global state manager and the routers
from .dependencies import app_state, get_qdrant_client
from .routers import search, images, duplicates, random, collections # and any others

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

    # Initialize ML Model
    # This ensures the model is loaded once on startup, not per-request
    model_name = "clip-ViT-B-32"
    app_state.ml_model = SentenceTransformer(model_name)
    logger.info(f"ML Model '{model_name}' loaded.")

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
    # Check Qdrant connection
    try:
        qdrant_info = app_state.qdrant_client.get_collections()
        qdrant_status = "ok"
    except Exception:
        qdrant_status = "error"

    # Check ML model
    ml_model_status = "ok" if app_state.ml_model else "error"

    if qdrant_status == "ok" and ml_model_status == "ok":
        return {"status": "ok", "services": {"qdrant": qdrant_status, "ml_model": ml_model_status}}
    else:
        raise HTTPException(status_code=503, detail={"status": "error", "services": {"qdrant": qdrant_status, "ml_model": ml_model_status}})


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

# --- Image Serving Endpoints ---
from fastapi.responses import FileResponse, Response
import io
import base64

@v1_router.get("/images/{image_id}/thumbnail")
async def get_image_thumbnail(image_id: str, q_client: QdrantClient = Depends(get_qdrant_client)):
    """Serve image thumbnail by ID - optimized for speed with base64 data"""
    if not app_state.active_collection:
        raise HTTPException(status_code=400, detail="No collection selected")
    
    try:
        # Get the image data from Qdrant
        result = q_client.retrieve(
            collection_name=app_state.active_collection,
            ids=[image_id],
            with_payload=True
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found")
        
        point = result[0]
        payload = point.payload
        
        # Fast path: use pre-generated thumbnail
        if "thumbnail_base64" in payload:
            thumbnail_data = base64.b64decode(payload["thumbnail_base64"])
            return Response(content=thumbnail_data, media_type="image/jpeg")
        
        # Fallback: use full image and create thumbnail
        image_data = None
        if "image_base64" in payload:
            image_data = base64.b64decode(payload["image_base64"])
        elif "full_path" in payload or "file_path" in payload:
            # Fast file system fallback - read from file path
            file_path = payload.get("full_path") or payload.get("file_path")
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    image_data = f.read()
        
        if not image_data:
            raise HTTPException(status_code=404, detail="Image data not found")
        
        # Create thumbnail on-the-fly (should rarely happen with new ingestion)
        try:
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85)
            thumbnail_data = img_byte_arr.getvalue()
            
            return Response(content=thumbnail_data, media_type="image/jpeg")
            
        except Exception as e:
            logger.error(f"Error creating thumbnail for {image_id}: {e}")
            # Return original image if thumbnail creation fails
            filename = payload.get("filename", "image.jpg")
            content_type = "image/jpeg"
            if filename.lower().endswith('.png'):
                content_type = "image/png"
            elif filename.lower().endswith('.gif'):
                content_type = "image/gif"
            elif filename.lower().endswith('.webp'):
                content_type = "image/webp"
            
            return Response(content=image_data, media_type=content_type)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving thumbnail for {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve image thumbnail")

@v1_router.get("/images/{image_id}/image")
async def get_full_image(image_id: str, q_client: QdrantClient = Depends(get_qdrant_client)):
    """Serve full resolution image by ID, prioritizing fast file system access"""
    if not app_state.active_collection:
        raise HTTPException(status_code=400, detail="No collection selected")
    
    try:
        # Get the image data from Qdrant
        result = q_client.retrieve(
            collection_name=app_state.active_collection,
            ids=[image_id],
            with_payload=True
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found")
        
        point = result[0]
        payload = point.payload
        
        # Fast path: use stored base64 data
        image_data = None
        if "image_base64" in payload:
            image_data = base64.b64decode(payload["image_base64"])
        elif "full_path" in payload or "file_path" in payload:
            # Fast file system fallback - read from file path
            file_path = payload.get("full_path") or payload.get("file_path")
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    image_data = f.read()
        
        if not image_data:
            raise HTTPException(status_code=404, detail="Image data not found")
        
        # Determine content type from filename
        filename = payload.get("filename", "image.jpg")
        if filename.lower().endswith('.png'):
            content_type = "image/png"
        elif filename.lower().endswith('.gif'):
            content_type = "image/gif"
        elif filename.lower().endswith('.webp'):
            content_type = "image/webp"
        elif filename.lower().endswith('.dng'):
            content_type = "image/jpeg"  # DNG is converted to JPEG during processing
        else:
            content_type = "image/jpeg"
        
        return Response(content=image_data, media_type=content_type)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve image")

# Finally, register v1_router with the main FastAPI app (do this once at the end)
app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 