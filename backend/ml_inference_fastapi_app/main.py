import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import torch

# Import the new service and router modules
from .services import clip_service, blip_service
from .routers import inference

# Configure logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # --- Startup ---
    logger.info("ML Inference Service starting up...")
    
    # Warm up models concurrently
    async with clip_service.gpu_lock:
        await clip_service.load_clip_model()
        clip_service.recalculate_safe_batch_size()
        
        await blip_service.load_blip_model()
        blip_service.recalculate_safe_batch_size()
    
    logger.info("Startup complete. Models are loaded and ready.")
    yield
    # --- Shutdown ---
    logger.info("ML Inference Service shutting down...")
    async with clip_service.gpu_lock:
        await clip_service.cooldown_clip_model()
        await blip_service.cooldown_blip_model()
    logger.info("Shutdown complete.")


# --- FastAPI App Initialization ---
app = FastAPI(
    title="ML Inference Service",
    lifespan=lifespan,
)

# CORS Middleware
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    # Add other origins as needed
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routers ---
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(inference.router) # Include the new inference router

app.include_router(v1_router)

# --- Basic Endpoints ---
@app.get("/")
async def root():
    return {"message": "ML Inference Service is running."}

@app.get("/health")
async def health():
    clip_ok = clip_service.get_clip_model_status()
    blip_ok = blip_service.get_blip_model_status()
    
    if clip_ok and blip_ok:
        return {"status": "ok", "clip_model": "ready", "blip_model": "ready"}
    else:
        raise HTTPException(status_code=503, detail={
            "status": "error",
            "clip_model": "ready" if clip_ok else "unavailable",
            "blip_model": "ready" if blip_ok else "unavailable",
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 