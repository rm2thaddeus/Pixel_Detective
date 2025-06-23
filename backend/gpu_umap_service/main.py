from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from umap_service.main import router as umap_router
from fastapi.responses import JSONResponse

app = FastAPI(title="GPU UMAP Service")

# Allow calls from the Next.js dev server (localhost:3000) and any origin during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(umap_router, prefix="/umap")

# Simple health-check endpoint so front-end and monitoring tools can verify
# that the GPU UMAP service is up and responsive. Mirrors the schema used by
# other micro-services in this project (see ingestion orchestration service).
@app.get("/health")
async def health():
    return JSONResponse({"service": "gpu_umap_service", "status": "ok"})
