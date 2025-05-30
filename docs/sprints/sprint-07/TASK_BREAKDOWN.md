# Sprint 07 Task Breakdown

This document breaks down the objectives from `PRD.md` into more granular tasks.

## Objective 1: Dockerize Ingestion Orchestration Service & Configure Local ML Service

*   **INF-07-01: Configure ML Inference Service for Local Execution**
    *   `[X]` Ensure `backend/ml_inference_fastapi_app/` can run directly on the host machine.
        *   `[X]` Verify Python environment and dependencies from `requirements.txt` are installed locally.
        *   `[X]` Confirm model caches (Hugging Face, CLIP) are accessible from local execution.
        *   `[X]` Test running the service locally (e.g., `uvicorn main:app --host 0.0.0.0 --port 8001`) and accessing its API endpoints.
*   **INF-07-02: Dockerize Ingestion Orchestration Service**
    *   `[ABANDONED]` Dockerization of Ingestion Orchestration Service is discontinued. Service will run locally. Only Qdrant will use Docker.
    *   `[ABANDONED]` All Docker-related tasks for this service are abandoned due to disk space and value concerns.
*   **INF-07-03: Update `docker-compose.yml` for hybrid setup**
    *   `[UPDATED]` Only Qdrant will run in Docker. All other services (ML Inference, Ingestion Orchestration) will run locally.
    *   `[UPDATED]` Docker Compose will only be used to manage Qdrant.
    *   `[X]` Inter-service communication and Qdrant persistence successfully tested: ML Inference Service processed images, and ingestion stored results in Qdrant ('development test' collection).

## Objective 2: Implement Persistent Cache

*   **SVC-07-01: Implement Persistent Cache in Ingestion Service**
    *   `[X]` Researched persistent cache solutions. **DiskCache** selected for its speed, reliability, and flexibility with local files and Docker volumes.
        *   DiskCache offers easy integration, high performance, and low resource footprint. Will be tested with local files and Docker volumes.
    *   `[X]` Modified `backend/ingestion_orchestration_fastapi_app/main.py` to use DiskCache as a persistent cache.
        *   `[X]` Replaced in-memory dictionary cache with DiskCache.
        *   `[X]` Cache is initialized on service startup and directory is configurable via `DISKCACHE_DIR` env variable.
        *   `[X]` Keys (image hashes) and values are stored and retrieved correctly.
        *   `[X]` Will test cache with local files and Docker volumes for persistence.
    *   `[N/A]` Update `docker-compose.yml` for `ingestion_orchestration_service` to mount a volume for the persistent cache data (not needed for local-only setup).
    *   `[X]` Test: Ingest a directory, stop/restart services, ingest again – confirmed DiskCache survived restart and cached images were skipped.

## Objective 3: Streamlit UI Integration (Phase 1 - Read Operations)

*   **UI-07-01: Develop API endpoints for UI data needs (Phase 1)**
    *   `[ ]` Identify data requirements for initial Streamlit screens (e.g., list of processed images with thumbnails/metadata, basic keyword search results).
    *   `[ ]` Design API endpoints in the Ingestion Orchestration Service (or a new UI-focused BFF service).
        *   Example: `/api/v1/images?page=1&limit=20`
        *   Example: `/api/v1/search?query=keyword&top_k=10`
    *   `[ ]` Implement these endpoints in the chosen FastAPI application.
        *   `[ ]` Endpoints should query Qdrant (via Qdrant client).
        *   `[ ]` Implement pagination, filtering, and sorting as needed.
    *   `[ ]` Test API endpoints thoroughly using tools like `curl` or Postman.
*   **UI-07-02: Integrate Streamlit UI with backend services (Phase 1 - Read)**
    *   `[ ]` Identify Streamlit scripts/components (`screens/`, `components/`) to be updated.
    *   `[ ]` Modify these components to fetch data from the new API endpoints instead of local/direct data access.
        *   `[ ]` Use `requests` or `httpx` library for making API calls.
        *   `[ ]` Update UI to handle loading states and display data from API responses.
        *   `[ ]` Ensure error handling for API call failures.
    *   `[ ]` Test UI pages to confirm data is displayed correctly and interactions are smooth.

## Objective 4: Continue Legacy Code Deprecation

*   **CLEAN-07-01: Continue legacy code deprecation (Phase 3 of S06 Plan)**
    *   `[ ]` Review `docs/sprints/sprint-06/SPRINT_06_REFACTOR_PLAN.md` (Phase 3 tasks).
    *   `[ ]` **Task 1 (Example): Refactor/Delete `core/fast_startup_manager.py`**
        *   `[ ]` Analyze remaining useful parts (e.g., instant UI shell).
        *   `[ ]` Migrate useful UI logic to relevant screen scripts or a new UI manager.
        *   `[ ]` Delete obsolete model loading and `StartupProgress` logic.
        *   `[ ]` Remove usages of `get_fast_startup_manager()`.
        *   `[ ]` Delete the file if fully superseded.
    *   `[ ]` **Task 2 (Example): Refactor/Analyze `components/task_orchestrator.py`**
        *   `[ ]` Identify and remove/refactor uses related to old monolithic ingestion.
        *   `[ ]` Determine if it's still needed for UI-side background tasks.
        *   `[ ]` Update its usage or deprecate if no longer necessary.
    *   `[ ]` **Task 3 (Example): Analyze and Refactor/Delete items from `utils/`**
        *   `[ ]` e.g., `utils/embedding_cache.py` - is it fully replaced by new service cache? If so, remove. If `mvp_app.py` still uses it for non-service features, plan its future.
    *   `[ ]` For each targeted module:
        *   `[ ]` Verify its functionality is covered by new services.
        *   `[ ]` Update or remove dependent code.
        *   `[ ]` Archive/delete the module.
        *   `[ ]` Update `SPRINT_06_REFACTOR_PLAN.md` with progress.
    *   `[ ]` Review remaining features in `scripts/mvp_app.py`.
        *   `[ ]` Identify features that should now use the new services (e.g., search functionality).
        *   `[ ]` Refactor these parts of `mvp_app.py` to make API calls to the services.

## Objective 5: Testing and Stability

*   **TEST-07-01: Develop tests for new services and Dockerized environment**
    *   `[ ]` Write unit tests for FastAPI services (`ml_inference_fastapi_app`, `ingestion_orchestration_fastapi_app`).
        *   `[ ]` Test API endpoint logic.
        *   `[ ]` Test helper functions/classes.
        *   `[ ]` Mock external dependencies (other services, DB) where appropriate for unit tests.
    *   `[ ]` Write integration tests.
        *   `[ ]` Test service-to-service communication (e.g., Ingestion -> ML, Ingestion -> Qdrant).
        *   `[ ]` Test against a real (test instance) Qdrant database.
    *   `[ ]` Develop/enhance end-to-end tests for the full ingestion pipeline using the Dockerized services.
        *   `[ ]` Use `scripts/batch_processing_client.py` to trigger ingestion.
        *   `[ ]` Verify data in Qdrant after ingestion.
        *   `[ ]` Verify persistent cache behavior.
    *   `[ ]` Ensure all tests pass consistently.

## Objective 6: Documentation

*   **DOC-07-01: Document Sprint 07 changes**
    *   `[ ]` Update `docs/sprints/sprint-06/README.md` with any final notes if needed.
    *   `[ ]` Create/Update `README.md` for `backend/ml_inference_fastapi_app/` including Dockerization instructions.
    *   `[ ]` Create/Update `README.md` for `backend/ingestion_orchestration_fastapi_app/` including Dockerization and persistent cache details.
    *   `[ ]` Update the main `docker-compose.yml` with comments explaining service configurations.
    *   `[ ]` Document new API endpoints for UI integration (e.g., in a Swagger/OpenAPI spec or a markdown file).
    *   `[ ]` Update overall project architecture diagrams (e.g., in `docs/ARCHITECTURE.md` or a shared diagramming tool) to reflect Dockerized services and UI interaction flow.
    *   `[ ]` Fill in Sprint 07 `README.md` (`docs/sprints/sprint-07/README.md`) upon sprint completion.

---
*Assign tasks to team members and track progress here or in a project management tool.* 