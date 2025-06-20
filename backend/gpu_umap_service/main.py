from fastapi import FastAPI
from .umap_service.main import router as umap_router

app = FastAPI(title="GPU UMAP Service")
app.include_router(umap_router, prefix="/umap")
