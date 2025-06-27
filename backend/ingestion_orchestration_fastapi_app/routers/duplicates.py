from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, PointStruct
from typing import List, Dict, Any
import logging
import uuid
import os
import shutil
from pydantic import BaseModel

from ..dependencies import get_qdrant_client, get_active_collection

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/api/v1/duplicates", tags=["duplicates"])

# In-memory storage for task status. In production, use Redis or a DB.
tasks = {}
# Track curation status per collection so the frontend can display progress
collection_curation_status: Dict[str, str] = {}


class FindSimilarTask(BaseModel):
    task_id: str
    status: str = "pending"
    progress: float = 0.0
    total_points: int = 0
    processed_points: int = 0
    results: List[Dict[str, Any]] = []


class ArchiveExactRequest(BaseModel):
    file_paths: List[str]


def find_similar_images_task(
    task_id: str,
    qdrant_client: QdrantClient,
    collection_name: str,
    threshold: float,
    limit_per_image: int,
):
    """
    Background task to find visually similar images in a collection.
    Iterates through all points and finds those with a cosine similarity above the threshold.
    """
    tasks[task_id].status = "running"

    collection_curation_status[collection_name] = "running"
    logger.info(f"Task {task_id}: Starting near-duplicate analysis for collection '{collection_name}'.")

    logger.info(
        f"Task {task_id}: Starting near-duplicate analysis for collection '{collection_name}'."
    )


    try:
        # Get total number of points for progress calculation
        collection_info = qdrant_client.get_collection(collection_name=collection_name)
        total_points = collection_info.points_count
        tasks[task_id].total_points = total_points

        processed_ids = set()
        duplicate_groups = []

        # Use scroll to iterate over all points in the collection
        scroll_response = qdrant_client.scroll(
            collection_name=collection_name,
            with_vectors=True,
            limit=100,  # Adjust batch size as needed
        )

        points_batch = scroll_response[0]
        next_page_offset = scroll_response[1]

        while points_batch:
            for i, point in enumerate(points_batch):
                if point.id in processed_ids:
                    continue

                # Update progress
                tasks[task_id].processed_points += 1
                tasks[task_id].progress = (
                    tasks[task_id].processed_points / total_points
                ) * 100
                if tasks[task_id].processed_points % 100 == 0:
                    logger.info(
                        f"Task {task_id}: Progress {tasks[task_id].progress:.2f}% ({tasks[task_id].processed_points}/{total_points})"
                    )

                search_results = qdrant_client.search(
                    collection_name=collection_name,
                    query_vector=point.vector,
                    query_filter=Filter(
                        must_not=[FieldCondition(key="id", match={"value": point.id})]
                    ),
                    score_threshold=threshold,
                    limit=limit_per_image,
                )

                if search_results:
                    # Found a group of similar images
                    current_group_ids = {point.id}
                    current_group_points = [
                        {"id": point.id, "payload": point.payload, "score": 1.0}
                    ]

                    for sr in search_results:
                        current_group_ids.add(sr.id)
                        current_group_points.append(
                            {"id": sr.id, "payload": sr.payload, "score": sr.score}
                        )

                    duplicate_groups.append(
                        {"group_id": str(uuid.uuid4()), "points": current_group_points}
                    )
                    processed_ids.update(current_group_ids)

            if next_page_offset is None:
                break

            # Fetch the next batch
            scroll_response = qdrant_client.scroll(
                collection_name=collection_name,
                with_vectors=True,
                limit=100,
                offset=next_page_offset,
            )
            points_batch = scroll_response[0]
            next_page_offset = scroll_response[1]

        tasks[task_id].results = duplicate_groups
        tasks[task_id].status = "completed"

        collection_curation_status[collection_name] = "completed"
        logger.info(f"Task {task_id}: Analysis complete. Found {len(duplicate_groups)} duplicate groups.")

        logger.info(
            f"Task {task_id}: Analysis complete. Found {len(duplicate_groups)} duplicate groups."
        )


    except Exception as e:
        logger.error(f"Task {task_id}: Failed with error: {e}", exc_info=True)
        tasks[task_id].status = "failed"
        collection_curation_status[collection_name] = "failed"


@router.post("/find-similar", status_code=202, response_model=FindSimilarTask)
async def find_similar(
    background_tasks: BackgroundTasks,
    threshold: float = Body(
        0.98, ge=0.8, le=1.0, description="Similarity threshold for duplicates."
    ),
    limit_per_image: int = Body(
        10, ge=1, le=50, description="Max duplicates per image."
    ),
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection),
):
    """
    Triggers a background task to find visually similar images in the collection.
    """
    task_id = str(uuid.uuid4())
    task = FindSimilarTask(task_id=task_id)
    tasks[task_id] = task

    collection_curation_status[collection_name] = "running"
    
=======


    background_tasks.add_task(
        find_similar_images_task,
        task_id,
        qdrant,
        collection_name,
        threshold,
        limit_per_image,
    )

    return task


@router.get("/report/{task_id}", response_model=FindSimilarTask)
async def get_similar_report(task_id: str):
    """
    Retrieves the status and results of a `find-similar` task.
    """
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/curation-status")
async def get_curation_statuses():
    """Return the current curation status for all collections."""
    return collection_curation_status
=======
@router.post("/archive-exact")
async def archive_exact_duplicates(
    req: ArchiveExactRequest,
):
    """Move the given file paths to a _VibeDuplicates folder on the same drive."""
    archived = []
    for path in req.file_paths:
        try:
            if os.path.exists(path):
                dest_dir = os.path.join(os.path.dirname(path), "_VibeDuplicates")
                os.makedirs(dest_dir, exist_ok=True)
                shutil.move(path, os.path.join(dest_dir, os.path.basename(path)))
                archived.append(path)
        except Exception as e:
            logger.error(f"Failed to archive {path}: {e}")
    return {"archived": archived}

