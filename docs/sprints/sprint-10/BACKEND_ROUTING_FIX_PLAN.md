# Backend Stability and Routing Fix Plan

> **Status:** 📝 **PLAN** - Ready for implementation  
> **Priority:** CRITICAL  
> **Related Docs:** `ARCHITECTURE_REVIEW.md`, `completion-summary.md`

---

## 1. Analysis of the Problem

The backend is currently unstable, especially during development with hot-reloading. The root cause is a **circular import dependency** between `main.py` and the router files (e.g., `routers/search.py`).

### The Vicious Cycle:
1.  `main.py` imports routers from `routers/*.py` to include their API endpoints.
2.  Router files (like `routers/search.py`) import the `app` object from `main.py` to access shared application state, such as the Qdrant client (`app.state.qdrant_client`) or the active collection.
3.  This `main.py` -> `routers/search.py` -> `main.py` loop crashes the Python importer, leading to the `Fatal Python error` and `AttributeError` during reloads.

The goal of this plan is to break this cycle using **Dependency Injection**, a standard practice in FastAPI that resolves this exact problem elegantly.

---

## 2. Proposed Solution: Dependency Injection

We will stop routers from importing `main.py` directly. Instead, we will provide dependencies (like the database client or configuration) to the router's path functions through FastAPI's `Depends` system.

We will use the existing `dependencies.py` file to manage the creation and retrieval of these shared resources.

### The New, Virtuous Flow:
1.  `main.py` initializes all resources (like the Qdrant client) on startup and stores them in a globally accessible (but safely managed) object.
2.  `dependencies.py` provides simple functions (e.g., `get_qdrant_client()`) that know how to retrieve these initialized resources.
3.  Router path functions declare their need for a resource using `Depends(get_qdrant_client)`.
4.  FastAPI handles providing the resource to the function when a request comes in.

This removes all imports of `main.py` from the routers, breaking the circular dependency and making the application stable, testable, and easier to maintain.

---

## 3. Step-by-Step Implementation Guide

### Step 1: Centralize Dependency Management (`dependencies.py`)

First, we will establish a simple, globally accessible "manager" to hold our application state. Then, we will create getter functions for our dependencies.

**File:** `backend/ingestion_orchestration_fastapi_app/dependencies.py`

```python
# backend/ingestion_orchestration_fastapi_app/dependencies.py

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# This is a simple container for our shared resources.
# It's a plain class, so it's easy to understand and doesn't hide any magic.
class AppState:
    def __init__(self):
        self.qdrant_client: QdrantClient | None = None
        self.ml_model: SentenceTransformer | None = None
        self.active_collection: str | None = None

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

```

### Step 2: Refactor `main.py` to Use the New State Manager

Next, we update the main application file to initialize resources into our `app_state` object during the startup event.

**File:** `backend/ingestion_orchestration_fastapi_app/main.py`

```python
# backend/ingestion_orchestration_fastapi_app/main.py
# (Showing only the relevant parts to change)

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Import the global state manager and the routers
from .dependencies import app_state
from .routers import search, images, duplicates, random # and any others

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager. This is the recommended way to manage
    startup and shutdown events in modern FastAPI.
    """
    # --- Startup ---
    print("INFO:     Starting up services...")
    
    # Initialize Qdrant Client
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = os.getenv("QDRANT_PORT", 6333)
    app_state.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
    print(f"INFO:     Qdrant client initialized for {qdrant_host}:{qdrant_port}")

    # Initialize ML Model
    # This ensures the model is loaded once on startup, not per-request
    model_name = "clip-ViT-B-32"
    app_state.ml_model = SentenceTransformer(model_name)
    print(f"INFO:     ML Model '{model_name}' loaded.")

    # Set a default active collection for demonstration
    app_state.active_collection = "my-first-collection"
    print(f"INFO:     Default active collection set to '{app_state.active_collection}'.")
    
    print("INFO:     Startup complete.")
    yield
    # --- Shutdown ---
    print("INFO:     Shutting down services...")
    if app_state.qdrant_client:
        # Qdrant client might have a close() method in some versions
        # app_state.qdrant_client.close()
        pass
    print("INFO:     Shutdown complete.")


# Create the FastAPI app instance with the lifespan manager
app = FastAPI(lifespan=lifespan)

# Include the routers
# Now, they don't need access to the `app` object anymore.
app.include_router(search.router)
app.include_router(images.router)
app.include_router(duplicates.router)
app.include_router(random.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Vibe Coding API"}

# Any other main app routes can go here. For example, a route to change the active collection.
@app.post("/api/v1/collections/select")
def select_collection(collection_name: str):
    """
    An endpoint to change the globally active collection.
    """
    # In a real application, you'd verify the collection exists first.
    app_state.active_collection = collection_name
    return {"message": f"Active collection changed to '{collection_name}'"}

```

### Step 3: Refactor Routers to Use `Depends`

Finally, we update the router(s) to get dependencies from the new provider functions. We will no longer import `main` or access `request.app`.

**File:** `backend/ingestion_orchestration_fastapi_app/routers/search.py`

```python
# backend/ingestion_orchestration_fastapi_app/routers/search.py
# (Showing only the relevant parts to change)

from fastapi import APIRouter, Depends, HTTPException
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel

# Import the dependency getters, NOT the main app
from ..dependencies import get_qdrant_client, get_ml_model, get_active_collection

router = APIRouter(
    prefix="/api/v1/search",
    tags=["search"]
)

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

class SearchResult(BaseModel):
    id: str | int
    score: float
    # Add other fields like image_url, etc.

# This is the key change.
# Instead of `request: Request`, we ask for the dependencies we need.
# FastAPI will call the getter functions and provide the return values.
@router.post("/", response_model=list[SearchResult])
async def search_images(
    search_request: SearchRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    ml_model: SentenceTransformer = Depends(get_ml_model),
    collection_name: str = Depends(get_active_collection)
):
    """
    Performs a vector search based on a text query.
    """
    # The `qdrant_client`, `ml_model`, and `collection_name` are now provided
    # directly as arguments, fully typed and ready to use.
    
    # 1. Encode the text query into a vector
    try:
        query_vector = ml_model.encode(search_request.query).tolist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to encode query: {e}")

    # 2. Perform the search in Qdrant
    try:
        hits = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=search_request.limit,
            with_payload=True # To get metadata
        )
    except Exception as e:
        # This can happen if the collection doesn't exist
        raise HTTPException(status_code=404, detail=f"Search failed. Collection '{collection_name}' may not exist or Qdrant is down. Error: {e}")

    # 3. Format the results
    results = [
        SearchResult(id=hit.id, score=hit.score) 
        for hit in hits
    ]

    return results

```
*You should apply a similar refactoring to the other router files (`images.py`, `duplicates.py`, `random.py`) if they also need access to shared state.*

---

## 4. Bonus Fix: `Enum` Serialization Error

The `completion-summary.md` also mentions that an API for collection creation returns a 500 error because a `Distance` enum from Qdrant is not JSON serializable.

**The Fix:** When returning data that might contain non-standard types, use FastAPI's `jsonable_encoder` or, even better, return a Pydantic model.

**Example (in a hypothetical `collections.py` router):**

```python
from fastapi import APIRouter
from pydantic import BaseModel
from qdrant_client import models

# Assume you have a router for collections

class CollectionInfo(BaseModel):
    name: str
    vector_size: int
    distance: str # Return the distance as a string

@router.get("/{collection_name}", response_model=CollectionInfo)
async def get_collection_details(collection_name: str, qdrant_client: QdrantClient = Depends(get_qdrant_client)):
    try:
        details = qdrant_client.get_collection(collection_name=collection_name)
        
        # Manually convert the Enum to a string for the Pydantic model
        return CollectionInfo(
            name=collection_name,
            vector_size=details.vectors_config.params.size,
            distance=str(details.vectors_config.params.distance) # Convert enum to string
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not get details for collection '{collection_name}'. Error: {e}")

```

---

## 5. Verification Plan

After implementing these changes:
1.  **Start the backend server:** `cd backend/ingestion_orchestration_fastapi_app && python main.py`
2.  **Observe the logs:** The server should start cleanly with no errors.
3.  **Test Hot-Reload:** Make a small, safe change to `main.py` (e.g., add a comment) and save it. The server should reload gracefully without crashing.
4.  **Test the Endpoint:** Use a tool like `curl` or the Swagger UI (`http://localhost:8002/docs`) to send a request to the `/api/v1/search/` endpoint. It should now work correctly.
5.  **Confirm Stability:** The application should remain stable even after multiple reloads and requests.

By following this plan, you will have a much more robust, stable, and maintainable backend architecture. 