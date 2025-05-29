from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
import httpx
import os
import logging
from database_utils.qdrant_connector import QdrantDB # Adjusted import path
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Environment variables for service URLs
ML_INFERENCE_SERVICE_URL = os.environ.get("ML_INFERENCE_SERVICE_URL", "http://ml_inference_service:8001")
# Qdrant connection details from environment variables, matching docker-compose
QDRANT_HOST = os.environ.get("QDRANT_HOST", "qdrant_db")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
QDRANT_COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "image_collection")

# Global Qdrant client instance
qdrant_db_client: QdrantDB = None

@app.on_event("startup")
async def startup_event():
    global qdrant_db_client
    logger.info("Ingestion Orchestration Service starting up.")
    try:
        qdrant_db_client = QdrantDB(
            collection_name=QDRANT_COLLECTION_NAME,
            host=QDRANT_HOST,
            port=QDRANT_PORT
        )
        logger.info(f"Successfully connected to QdrantDB at {QDRANT_HOST}:{QDRANT_PORT}, collection: {QDRANT_COLLECTION_NAME}")
        # You might want to check collection info or ensure it's ready
        # info = qdrant_db_client.get_collection_info()
        # logger.info(f"Qdrant collection info: {info}")
    except Exception as e:
        logger.error(f"Failed to connect to QdrantDB during startup: {e}", exc_info=True)
        # Decide if service should fail to start or run degraded (qdrant_db_client will be None)
        qdrant_db_client = None # Ensure it's None if connection failed

@app.post("/process-batch")
async def process_batch(batch_data: dict):
    global qdrant_db_client
    if not qdrant_db_client:
        logger.error("QdrantDB client is not available. Cannot process batch.")
        raise HTTPException(status_code=503, detail="Database service is not available.")

    image_paths = batch_data.get("image_paths", [])
    if not image_paths:
        raise HTTPException(status_code=400, detail="'image_paths' not provided or empty.")
    
    results = []
    processed_count = 0
    error_count = 0

    async with httpx.AsyncClient(timeout=None) as client:
        for image_path in image_paths:
            try:
                logger.info(f"Processing image: {image_path}")
                # 1. Get embedding
                embed_response = await client.post(f"{ML_INFERENCE_SERVICE_URL}/embed", json={"image_path": image_path})
                embed_response.raise_for_status()
                embedding_data = embed_response.json()
                embedding = embedding_data.get("embedding")

                # 2. Get caption
                caption_response = await client.post(f"{ML_INFERENCE_SERVICE_URL}/caption", json={"image_path": image_path})
                caption_response.raise_for_status()
                caption_data = caption_response.json()
                caption = caption_data.get("caption")

                # 3. Placeholder for richer metadata extraction
                # For now, just using path and extracted elements.
                # TODO: Integrate utils.metadata_extractor.py if it exists and is relevant
                metadata = {
                    "source_path": image_path,
                    "caption": caption,
                    # Add other relevant metadata: file_size, creation_date, image_dimensions etc.
                }

                # 4. Store in Qdrant
                # Note: qdrant_connector.add_image expects embedding to be a list or ndarray
                if embedding and caption is not None: # Ensure we have key data
                    # The QdrantDB class expects metadata to be the payload.
                    # The `add_image` method in QdrantDB also adds 'filename' and 'path' to payload.
                    success = qdrant_db_client.add_image(
                        image_path=image_path, 
                        embedding=embedding, 
                        metadata=metadata
                    )
                    if success:
                        logger.info(f"Successfully stored in Qdrant: {image_path}")
                        results.append({
                            "image_path": image_path,
                            "status": "success",
                            "embedding_stored": True,
                            "caption_stored": caption
                        })
                        processed_count += 1
                    else:
                        logger.error(f"Failed to store in Qdrant: {image_path}")
                        results.append({"image_path": image_path, "status": "error", "detail": "Failed to store in Qdrant"})
                        error_count += 1
                else:
                    logger.warning(f"Missing embedding or caption for {image_path}, skipping Qdrant storage.")
                    results.append({"image_path": image_path, "status": "error", "detail": "Missing embedding or caption from ML service"})
                    error_count += 1

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling ML service for {image_path}: {e.response.status_code} - {e.response.text}", exc_info=True)
                results.append({"image_path": image_path, "status": "error", "detail": f"ML service error: {e.response.status_code}"})
                error_count += 1
            except Exception as e:
                logger.error(f"Unexpected error processing {image_path}: {e}", exc_info=True)
                results.append({"image_path": image_path, "status": "error", "detail": f"Unexpected error: {str(e)}"})
                error_count += 1

    return {"message": f"Batch processing finished. Processed: {processed_count}, Errors: {error_count}", "results": results}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Ingestion Orchestration Service for local debugging...")
    # For local debugging, ensure QDRANT_HOST points to your local Qdrant instance if not using docker-compose
    # And ML_INFERENCE_SERVICE_URL points to where that service is running.
    uvicorn.run(app, host="0.0.0.0", port=8002) 