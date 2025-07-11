import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
from typing import Dict, Any, Optional
from pydantic import BaseModel
import diskcache
from PIL import Image
import asyncio

# Local utilities & deps
from .dependencies import app_state, get_qdrant_client

# Dynamic batch-size helper (runs in lifespan → sets env vars before heavy work)
from .utils import autosize

# Routers – imported *after* helper to ensure any module-level constants read the
# finalised environment variables.
from .routers import search, images, duplicates, random, collections, umap, curation, ingest

# Configure logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


# --- App State ---
# The AppState class and app_state instance are now managed in `dependencies.py`
# to avoid circular imports and provide a single source of truth for application state.


# --- Pydantic Models ---
class CapabilitiesResponse(BaseModel):
    ml_batch_size: int
    qdrant_batch_size: int
    is_ready_for_ingestion: bool
    active_collection: Optional[str] = None
    ml_service_url: str

class IngestRequest(BaseModel):
    pass  # Placeholder for now

class IngestResponse(BaseModel):
    job_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager. This is the recommended way to manage
    startup and shutdown events in modern FastAPI.
    """
    # --- Startup ---
    logger.info("Starting up services...")
    
    # ------------------------------------------------------------------
    # 0️⃣  Dynamically size batch parameters (RAM-aware)
    # ------------------------------------------------------------------
    await autosize.autosize_batches(
        os.getenv("ML_INFERENCE_SERVICE_URL", "http://localhost:8001")
    )
    app_state.is_ready_for_ingestion = autosize.CAPABILITIES_FETCHED
    
    # ------------------------------------------------------------------
    # Env-var aliasing – ensure both ML_SERVICE_URL and ML_INFERENCE_SERVICE_URL
    # are populated to avoid mismatches across routers/modules.
    # ------------------------------------------------------------------
    if "ML_SERVICE_URL" not in os.environ and "ML_INFERENCE_SERVICE_URL" in os.environ:
        os.environ["ML_SERVICE_URL"] = os.environ["ML_INFERENCE_SERVICE_URL"]
        logger.info("Aliased ML_SERVICE_URL → %s", os.environ["ML_SERVICE_URL"])

    if "ML_INFERENCE_SERVICE_URL" not in os.environ and "ML_SERVICE_URL" in os.environ:
        os.environ["ML_INFERENCE_SERVICE_URL"] = os.environ["ML_SERVICE_URL"]
        logger.info("Aliased ML_INFERENCE_SERVICE_URL → %s", os.environ["ML_INFERENCE_SERVICE_URL"])

    # Ensure routers that cached the old env vars pick up the new values
    try:
        from .routers import ingest as ingest_router  # local import to avoid cycles

        ingest_router.ML_BATCH_SIZE = int(os.getenv("ML_INFERENCE_BATCH_SIZE", ingest_router.ML_BATCH_SIZE))
        ingest_router.QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", ingest_router.QDRANT_BATCH_SIZE))
        logger.info(
            "[lifespan] Ingest router batching updated – ML:%s  Qdrant:%s",
            ingest_router.ML_BATCH_SIZE,
            ingest_router.QDRANT_BATCH_SIZE,
        )
    except Exception as e:
        logger.warning("[lifespan] Could not refresh ingest router batch constants: %s", e)

    # Refresh pipeline stage batch constants so GPU and DB workers use updated sizes
    try:
        from .pipeline import gpu_worker, db_upserter
        gpu_worker.ML_BATCH_SIZE = int(os.getenv("ML_INFERENCE_BATCH_SIZE", gpu_worker.ML_BATCH_SIZE))
        db_upserter.QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", db_upserter.QDRANT_BATCH_SIZE))
        logger.info(
            "[lifespan] Pipeline batch constants updated – GPU:%s  DB:%s",
            gpu_worker.ML_BATCH_SIZE,
            db_upserter.QDRANT_BATCH_SIZE,
        )
    except Exception as e:
        logger.warning("[lifespan] Could not refresh pipeline batch constants: %s", e)

    # ------------------------------------------------------------------
    # 1️⃣  Initialize Qdrant Client
    # ------------------------------------------------------------------
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
    app_state.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
    logger.info(f"Qdrant client initialized for {qdrant_host}:{qdrant_port}")

    # --- NEW: Wait for Qdrant to be healthy before proceeding ---
    max_retries = 10
    retry_delay_seconds = 5
    for attempt in range(max_retries):
        try:
            logger.info(f"Checking Qdrant health (attempt {attempt + 1}/{max_retries})...")
            # A simple operation to confirm connectivity and readiness
            app_state.qdrant_client.get_collections()
            logger.info("Qdrant is healthy. Proceeding with startup.")
            break
        except Exception as e:
            logger.warning(f"Qdrant not ready yet: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay_seconds)
            else:
                logger.error("Qdrant health check failed after multiple retries. The service might be unavailable.")
                # Depending on requirements, you might want to raise an exception here
                # to prevent the service from starting in a broken state.
                # For now, we'll log the error and continue, but endpoints will likely fail.

    # Note: We don't load ML models here anymore - we use the ML service via HTTP
    app_state.ml_service_url = os.getenv("ML_INFERENCE_SERVICE_URL", "http://localhost:8001")
    logger.info("Using ML service at %s for embeddings", app_state.ml_service_url)

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

# ---------------------------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------------------------
# Allow configurable front-end origins via env var. Multiple origins can be
# supplied comma-separated, e.g.:
#   FRONTEND_ORIGINS="http://localhost:3000, http://10.5.0.2:3000"
# Defaults cover common local development hosts.
# ---------------------------------------------------------------------------

_default_frontend_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Read env var (if provided) and merge with defaults – de-duplicate while
# preserving order.
frontend_origins_env = os.getenv("FRONTEND_ORIGINS", "")
_extra_origins = [o.strip() for o in frontend_origins_env.split(",") if o.strip()]
allowed_origins = []
for origin in _default_frontend_origins + _extra_origins:
    if origin not in allowed_origins:
        allowed_origins.append(origin)

# NOTE: allow_credentials=True means we cannot use the wildcard "*".
#       If the user truly wants open CORS they can set FRONTEND_ORIGINS="*"
#       _and_ we will disable credentials automatically.

allow_credentials_flag = True
allow_origin_regex = None

if len(allowed_origins) == 1 and allowed_origins[0] == "*":
    # Wildcard origin requested – switch to regex to satisfy FastAPI constraints
    allowed_origins = []  # Empty list when using regex
    allow_origin_regex = ".*"
    allow_credentials_flag = False  # Credentials cannot be used with wildcard

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=allow_credentials_flag,
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
            client = get_qdrant_client()
            client.get_collections()
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


@app.get("/api/v1/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities():
    """Returns the current operational capabilities of the ingestion service."""
    return CapabilitiesResponse(
        ml_batch_size=int(os.environ.get("ML_INFERENCE_BATCH_SIZE", "1")),
        qdrant_batch_size=int(os.environ.get("QDRANT_UPSERT_BATCH_SIZE", "1")),
        is_ready_for_ingestion=app_state.is_ready_for_ingestion,
        active_collection=app_state.active_collection,
        ml_service_url=app_state.ml_service_url,
    )


@app.post("/api/v1/ingest", response_model=IngestResponse, status_code=202)
async def schedule_ingestion(
    request: IngestRequest
):
    # Placeholder for now
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
