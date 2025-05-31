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
    *   `[x]` Identify data requirements for initial Streamlit screens (e.g., list of processed images with thumbnails/metadata, basic keyword search results).
    *   `[x]` Design API endpoints in the Ingestion Orchestration Service (or a new UI-focused BFF service).
        *   Example: `/api/v1/images?page=1&limit=20`
        *   Example: `/api/v1/search?query=keyword&top_k=10`
    *   `[x]` Implement these endpoints in the chosen FastAPI application.
        *   `[x]` Endpoints should query Qdrant (via Qdrant client).
        *   `[x]` Implement pagination, filtering, and sorting as needed.
    *   `[x]` Test API endpoints thoroughly using tools like `curl` or Postman.
*   **UI-07-02: Integrate Streamlit UI with backend services (Phase 1 - Read)**
    *   `[x]` Identify Streamlit scripts/components (`screens/`, `components/`) to be updated.
    *   `[x]` Modify these components to fetch data from the new API endpoints instead of local/direct data access.
        *   `[x]` Use `requests` or `httpx` library for making API calls. (Now fully `httpx.AsyncClient`)
        *   `[x]` Update UI to handle loading states and display data from API responses. (Now fully async)
        *   `[x]` Ensure error handling for API call failures.
    *   `[x]` Test UI pages to confirm data is displayed correctly and interactions are smooth. (Pending full user validation after async refactor)
*   **UI-07-03: Async Refactor of Frontend (Based on `o3research.md` and `RECONNECT_UI_REFACTOR_PLAN.md`)**
    *   `[x]` Refactor `frontend/core/service_api.py` to use `httpx.AsyncClient` and `async def` functions.
    *   `[x]` Update `INGESTION_ORCHESTRATION_URL` in `service_api.py` to correct port (8002).
    *   `[x]` Refactor `frontend/app.py` to use an `async def main_async()` loop.
    *   `[x]` Refactor `frontend/core/screen_renderer.py` and its main `render_app` function to be asynchronous.
    *   `[x]` Refactor individual screen rendering functions in `frontend/screens/` (`fast_ui_screen.py`, `loading_screen.py`, `advanced_ui_screen.py`) to be `async def` and `await` API calls.
    *   `[x]` Refactor `frontend/core/background_loader.py` methods (`start_loading_pipeline`, `check_ingestion_status`) to be `async def` and `await` calls to the async `service_api.py`.
    *   `[x]` Add `httpx` to `frontend/requirements.txt`.

> The advanced UI screen is now fully decoupled from local model/DB logic and interacts only via HTTP APIs through the service API layer. Duplicate detection and some advanced features are pending backend support. The frontend is now fully asynchronous for API interactions.

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

## Sprint 07 Wrap-up

- FastAPI endpoints for image listing, search, and ingestion status were implemented; endpoints for duplicate detection, random image, and advanced filtering are pending (see BACKLOG.md).
- CORS is enabled for all FastAPI services.
- Frontend ingestion orchestration URL fixed to port 8002.
- Frontend refactored to be fully asynchronous for API calls using `httpx.AsyncClient`, impacting `service_api.py`, `app.py`, `screen_renderer.py`, screen modules, and `background_loader.py`.
- End-to-end integration is functional for all core features; further E2E and integration testing is planned.
- All major sprint documentation has been updated. See BACKLOG.md for remaining work and next steps.
- All UI decoupling and service API integration tasks are complete.

*Assign tasks to team members and track progress here or in a project management tool.* 