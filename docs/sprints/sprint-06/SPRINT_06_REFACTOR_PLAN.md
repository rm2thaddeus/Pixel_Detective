# Sprint 06 Refactoring Plan: Service Modularization (FastAPI-first for ML/Ingestion)

This document outlines the steps and components affected by the transition to a service-oriented architecture as defined in `docs/sprints/sprint-06/PRD.md`.
**Key Change for this Sprint**: The `ML Inference Service` and `Ingestion Orchestration Service` will be developed as FastAPI applications intended to be run directly (e.g., via Uvicorn), not containerized with Docker for this sprint. Qdrant may still be run via Docker.
**Source Prioritization**: Logic from the `/core` directory (e.g., `core/optimized_model_manager.py`, `core/background_loader.py`) is considered the most up-to-date and should be prioritized for migration into the new services.

**Legend:**
*   **[C] Create**: New component/service.
*   **[M] Migrate**: Existing logic to be moved to a new service.
*   **[U] Update**: Existing component to interact with new services.
*   **[D] Deprecate/Delete**: Logic/component to be removed after migration.
*   **[K] Keep**: Component largely unchanged but may need minor adjustments.

---

**Overall Architecture Goal:**

*   **ML Inference Service (FastAPI App)**: Handles all model loading and predictions (CLIP, BLIP). Runs as a standalone FastAPI application.
*   **Database Service**: Qdrant instance (can be run via Docker or natively).
*   **Ingestion Orchestration Service (FastAPI App)**: Manages the workflow of processing files, calling ML Inference, and storing results in the Database Service. Runs as a standalone FastAPI application.
*   **Client (e.g., `scripts/mvp_app.py` or new)**: Initiates the ingestion process by calling the Ingestion Orchestration Service.
*   **Streamlit UI (Future Sprint)**: Will eventually interact with these services.

---

**Phase 1: Service Creation & Core Logic Migration (FastAPI Focus)**

1.  **[C] ML Inference Service (`backend/ml_inference_fastapi_app/`)**
    *   **Source Files for Logic/Models (prioritize logic from `core/optimized_model_manager.py`):**
        *   Primary: Relevant model loading, management, and inference functions from `core/optimized_model_manager.py`.
        *   Reference: `models/clip_model.py` and `models/blip_model.py` (for foundational model interaction patterns, if needed, but defer to `core/` logic if different).
    *   **Tasks**:
        *   `[X]` Create FastAPI application (`main.py`).
        *   `[X]` Create `requirements.txt` for this service.
        *   `[X]` **[M]** Migrate model loading (for CLIP and BLIP) and inference logic (for embeddings and captions) to this service.
            *   `[X]` This logic should primarily come from `core/optimized_model_manager.py` (adapted, focusing on core loading from `models/clip_model.py` & `models/blip_model.py`).
            *   `[X]` Implement model loading to occur on FastAPI service startup.
            *   `[X]` Expose inference capabilities via API endpoints (e.g., `/embed` for CLIP, `/caption` for BLIP).
        *   `[X]` **(N/A for this sprint)** ~~Create `Dockerfile` for this service.~~
        *   `[X]` **[D]** Direct usage of `models/clip_model.py`, `models/blip_model.py`, and model-specific logic within `core/optimized_model_manager.py` from outside this service will be deprecated. (Archived to `docs/archive/sprint_06_service_superseded_models/` and `docs/archive/sprint_06_service_superseded_managers/` respectively).
            *   (Details for `core/optimized_model_manager.py` refactoring remain largely the same as outlined in Phase 3, but confirm all its ML-specific responsibilities are moved here).

2.  **[C] Database Service (Qdrant)**
    *   **Source Files for Logic/Models**: N/A (Using Qdrant).
    *   **Tasks**:
        *   `[X]` Decision: Use Docker for local development.
        *   `[X]` If Docker: Ensure Qdrant is run with a volume mount for data persistence (e.g., `-v $(pwd)/qdrant_data:/qdrant/storage` in `docker run` or equivalent in `docker-compose.yml`).
        *   `[X]` Ensure Qdrant client libraries are available for the Ingestion Orchestration Service (add `qdrant-client` to its `requirements.txt`).
        *   `[X]` Use Qdrant client to store embeddings, captions, and metadata in the Database Service.
        *   `[X]` Implement status reporting/logging for ingestion tasks.
        *   `[ ]` **(N/A for this sprint)** ~~Create `Dockerfile` for this service.~~
        *   `[X]` **[D]** Existing direct database population logic in scripts will be replaced by calls to this service. (`database/db_manager.py` and `database/vector_db.py` deleted).

3.  **[C] Ingestion Orchestration Service (`backend/ingestion_orchestration_fastapi_app/`)**
    *   **Source Files for Logic/Models (prioritize logic from `core/background_loader.py`):**
        *   Primary: `core/background_loader.py` (for the main ingestion pipeline, file processing, orchestration, and interaction with ML/DB components).
        *   Reference: Potentially parts of `scripts/mvp_app.py` (for client interaction patterns or specific workflow triggers, if not covered by `core/background_loader.py`).
        *   Reference: `components/task_orchestrator.py` (for general background task management concepts, if adaptable to a service context).
    *   **Tasks**:
        *   `[X]` Create FastAPI application (`main.py`).
        *   `[X]` Create `requirements.txt` for this service.
        *   `[X]` Define API endpoint to receive batch processing requests (e.g., `/ingest_directory`).
        *   `[X]` **[M]** Implement logic to iterate through files in the given directory.
        *   `[X]` Call ML Inference Service (running FastAPI app) (`/embed`) to get embeddings.
        *   `[X]` Call ML Inference Service (running FastAPI app) (`/caption`) to get captions.
        *   `[X]` **[M]** Extract other necessary metadata.
        *   `[X]` Use Qdrant client to store embeddings, captions, and metadata in the Database Service.
        *   `[X]` Implement status reporting/logging for ingestion tasks.
        *   `[ ]` **(N/A for this sprint)** ~~Create `Dockerfile` for this service.~~
        *   `[ ]` **[D]** Existing direct database population logic in scripts will be replaced by calls to this service.

**Phase 2: Docker Compose & Client Adaptation (Revised)**

4.  **[C/U] Docker Compose Configuration (`docker-compose.yml`) - If Used for Qdrant**
    *   **Tasks**:
        *   `[X]` If running Qdrant via Docker:
            *   `[X]` Define `database_service` (Qdrant). (Already defined as `qdrant_db`)
            *   `[X]` Configure ports for Qdrant. (Already configured)
            *   `[X]` Configure persistent volumes for Qdrant. (Already configured using bind mount `./qdrant_storage`)
        *   `[X]` **(N/A for this sprint)** ~~Define `ml_inference_service`, `ingestion_orchestration_service`.~~ (Commented out existing Dockerized services as FastAPI apps will run locally)
        *   `[X]` **(N/A for this sprint)** ~~Configure networking for inter-service communication (FastAPI apps will call each other directly via HTTP, e.g., `http://localhost:port`).~~
        *   `[X]` **(N/A for this sprint)** ~~Define build contexts for custom services.~~

5.  **[U] Client Script (`scripts/batch_processing_client.py`)**
    *   **Tasks**:
        *   `[X]` **[U/M]** ~~Modify/create script to remove direct model loading and database interaction.~~ (`scripts/batch_processing_client.py` updated and will serve as the new client. Direct model/DB interaction was not present in its previous form, now calls service.)
        *   `[X]` It should make an HTTP request to the Ingestion Orchestration Service's API (e.g., POST to `http://localhost:8002/ingest_directory`). (Implemented in `scripts/batch_processing_client.py`)
        *   `[X]` Handle response from the Ingestion Service. (Implemented in `scripts/batch_processing_client.py`)
        *   `[X]` **[D]** ~~Remove old direct calls.~~ (N/A for `batch_processing_client.py` as it was already an HTTP client; ingestion logic in `mvp_app.py` is effectively deprecated by this change if `batch_processing_client.py` becomes the primary client for this task, as suggested in section 11 of the plan).

**Phase 3: Deprecation and Cleanup**
    *   (This phase remains largely the same, but the context shifts. Deprecated core logic moves to the FastAPI services instead of Dockerized services. The goal is still to simplify the main application by offloading responsibilities.)

6.  **Core Logic (`core/`)**
    *   `core/optimized_model_manager.py`:
        *   `[X]` **[U/D]** (Covered in Phase 1) Post-migration of its core responsibilities (CLIP/BLIP loading to ML Inference FastAPI App, `get_image_understanding_orchestrated` to Ingestion Orchestration FastAPI App), assess remaining parts. (File archived to `docs/archive/sprint_06_service_superseded_managers/optimized_model_manager.py`)
            *   `[X]` The specific logic for background loading, queuing, and state tracking of CLIP/BLIP models will be re-implemented or adapted within the ML Inference FastAPI App.
            *   `[X]` The `get_image_understanding_orchestrated` method and its associated logic will be **[M] Migrated** to the `Ingestion Orchestration FastAPI App`, which will call the ML Inference FastAPI App for individual model predictions.
            *   `[X]` UI-facing status methods (`is_model_ready`, `get_loading_status`, etc.) in this manager will be **[D] Deprecated**. The UI will get status from the Ingestion Orchestration FastAPI App in the future.
            *   `[X]` The `@st.cache_resource` caching for `get_optimized_model_manager()` will be **[D] Deprecated**.
            *   `[X]` After migration of these key parts, analyze if any *other* logic within `core/optimized_model_manager.py` remains relevant for the Streamlit application (e.g., managing other non-ML assets, different types of models *not* going into the ML service, or UI-specific model interactions). Such parts would be kept and refactored. Otherwise, its use by the main application will be largely **[D] Deprecated** and the file eventually deleted. (Archived for now).
    *   `core/fast_startup_manager.py`:
        *   `[ ]` **[U/D] Analyze**: Its primary role is to orchestrate UI rendering while `OptimizedModelManager` loads models. With ML models moving to a service, this core responsibility is obsolete.
            *   `[ ]` The logic for `_background_preload_worker` and direct interactions with `OptimizedModelManager` (`preload_models_async`, `are_all_models_ready`, model load callbacks) will be **[D] Deleted**.
            *   `[ ]` The `MODEL_PRELOAD` phase and related states in `StartupProgress` will be **[D] Removed or re-purposed** (e.g., to reflect service availability or task status from Ingestion Service).
            *   `[ ]` The concept of rendering an "instant UI" (`_render_instant_ui` and its sub-renderers) is valuable and could be **[K] Kept and [U] Refactored**. This refactored version would set up the initial UI shell and prepare for interaction with backend services, not local model loading.
            *   `[ ]` Alternatively, the UI rendering aspects could be merged into main screen scripts (e.g., `screens/fast_ui_screen.py` or an app setup module) and `FastStartupManager` itself **[D] Deprecated**.
            *   `[ ]` The `@st.cache_resource` caching for `get_fast_startup_manager()` fate depends on whether the manager is kept in a refactored form.
    *   `core/background_loader.py`:
        *   `[X]` **[D] Deprecate/Delete**: (Deleted)
            *   `[X]` **[M] Migrated** to the `Ingestion Orchestration Service (FastAPI App)`. This service will call the `ML Inference Service (FastAPI App)` and `Database Service (Qdrant)`.
            *   `[X]` The `prepare_heavy_modules()` functionality is **[D] Deprecated** for the main Streamlit application, as services will manage their own dependencies. The Streamlit app should become much lighter.
            *   `[X]` Progress tracking concepts (`LoadingProgress`, `LoadingPhase`) are still valid but will be re-implemented in the `Ingestion Orchestration FastAPI App` and exposed via an API for the UI.
            *   `[X]` Given the comprehensive shift of its responsibilities, this file is expected to be fully deprecated and deleted.
            *   `[X]` **Note**: This heavily implies that `database/db_manager.py` will also need significant refactoring or its logic absorbed into the `Ingestion Orchestration FastAPI App` (details for `db_manager.py` will be handled separately if it becomes a focus).
    *   `core/background_loader_broken.py`:
        *   `[X]` **[D] Delete**: Verify this is non-functional or experimental and remove it from the codebase.
    *   `core/app_state.py`:
        *   `[ ]` **[K] Keep**: Likely manages UI state. Will require **[U] Update** in future sprints to work with data from services.
    *   `core/screen_renderer.py`:
        *   `[ ]` **[K] Keep**: Likely handles UI rendering. Will require **[U] Update** in future sprints.

7.  **Components (`components/`)**
    *   `components/task_orchestrator.py`:
        *   `[ ]` **[K] Keep/Analyze**: This is a generic background thread task runner.
            *   `[ ]` Its use for submitting tasks that were part of the old monolithic data ingestion pipeline (e.g., tasks that directly accessed local models or built parts of the local database, like `render_duplicates_tab` if it operated on a local DB) is **[D] Deprecated**. These functionalities will now be handled by the `Ingestion Orchestration FastAPI App`.
            *   `[ ]` **[U] Update**: Calls to `submit()` for such ingestion-related tasks must be removed or refactored to interact with the new services (likely by making an API call to the Ingestion Orchestration FastAPI App and then potentially using `TaskOrchestrator` to manage polling that service for status from the UI, if a simple fire-and-forget is not desired for the UI).
            *   `[ ]` **[K] Keep**: Can be kept as a utility for managing purely UI-side, non-data-pipeline-related background tasks within the Streamlit process itself, if any exist (e.g., complex UI calculations, animations, non-critical background updates not tied to core data services).
    *   `components/performance_optimizer.py`:
        *   `[ ]` **[K] Keep/Analyze**: Contains a mix of general performance utilities and attempts to optimize loading of modules, some of which will move to services.
            *   `[ ]` **[D] Deprecate**: Attempts to lazy-load or optimize the loading of specific modules related to the ML models or data processing pipeline (e.g., `implement_code_splitting` if it targets `models.image_search`, `models.similarity_search` that used local models) are now obsolete as these modules/logic will reside in services.
            *   `[ ]` **[K] Keep & [U] Re-evaluate**: General utilities like `lazy_import` (if used for UI modules), `optimize_memory_usage`, `optimize_css_delivery`, `measure_startup_performance`, and `create_performance_dashboard` can be kept. Their relevance and effectiveness should be re-evaluated for the new, lighter Streamlit UI. The definition of "startup" for `measure_startup_performance` will pertain to the Streamlit app's own load time, not local ML model loading.
            *   `[ ]` **[U] Update**: Review all module names targeted by `lazy_import` or `implement_code_splitting` to ensure they are still relevant for the Streamlit frontend and not parts of the backend services.
    *   `components/accessibility.py`, `components/skeleton_screens.py` (and sub-directories like `sidebar/`, `visualization/`, `search/`):
        *   `[ ]` **[K] Keep**: These are UI-specific. Will require **[U] Update** in future sprints to integrate with the new service-based backend.

8.  **Models (`models/`)**
    *   `models/model_manager.py`:
        *   `[X]` **[D] Deprecate/Delete**: This manager duplicates/overlaps with `core/optimized_model_manager.py` and its core responsibilities (loading, managing CLIP/BLIP, inference, async preloading) are superseded by the new service architecture. (Archived to `docs/archive/sprint_06_service_superseded_managers/model_manager.py`)
            *   `[X]` Logic for direct model interaction (`process_image`, `generate_caption`, `get_image_understanding`) will be conceptually migrated to the `Ingestion Orchestration FastAPI App` (which calls the `ML Inference FastAPI App`).
            *   `[X]` The embedding caching mechanism (`get_cache`, `compute_sha256`) is valuable and needs **[M] Migration Analysis** – determine if this caching logic should be moved to the `Ingestion Orchestration FastAPI App` or be part of the `Database Service (Qdrant)` interaction strategy. (New caching implemented in Ingestion Service. Old cache utility in `utils/embedding_cache.py` potentially still used by `mvp_app.py` - analyze `utils` later).
            *   `[X]` Given the comprehensive shift, this file is expected to be fully deprecated and deleted from the main application. (Archived for now).
    *   `models/clip_model.py`:
        *   `[X]` **[D] Deprecate/Delete from main app**: The core logic contained within this file (e.g., `load_clip_model`, `unload_clip_model`, `process_image` – the actual model loading from disk/HuggingFace and inference code) will be **[M] Migrated** into internal modules of the new `ML Inference FastAPI App`. (Archived to `docs/archive/sprint_06_service_superseded_models/clip_model.py`)
        *   `[X]` This file should be deleted from the main application's `models/` directory once its functionality is self-contained within the `ML Inference FastAPI App`. (Archived).
    *   `models/blip_model.py`:
        *   `[X]` **[D] Deprecate/Delete from main app**: Similar to `clip_model.py`, its core logic (e.g., `load_blip_model`, `unload_blip_model`, `generate_caption`) will be **[M] Migrated** into internal modules of the new `ML Inference FastAPI App`. (Archived to `docs/archive/sprint_06_service_superseded_models/blip_model.py`)
        *   `[X]` This file should be deleted from the main application's `models/` directory once its functionality is self-contained within the `ML Inference FastAPI App`. (Archived).

9.  **Database (`database/`)**
    *   `database/db_manager.py`:
        *   `[X]` **[D] Deprecate/Delete**: (Deleted)
            *   `[X]` **[M] Migrated to Ingestion Orchestration Service (FastAPI App)**: Logic for `get_image_list`, `build_database` workflow, metadata extraction, and writing data to Qdrant.
            *   `[X]` **[D] Deprecated**: Direct calls to `model_manager`. The Ingestion Service will call the `ML Inference FastAPI App` API.
            *   `[X]` **[D] Deprecated (Recommend for Sprint 06)**: Saving embeddings and metadata to local `.npy` and `.csv` files. Focus on Qdrant as the primary data store via the `Database Service`.
            *   `[X]` **[D] Deprecated**: Querying methods (`load_database`, `search_similar_images`, `find_duplicate_images`, etc.) as implemented. Future UI will interact with new backend services for these functionalities.
            *   `[X]` **[D] Deprecated**: The constructor taking `model_manager`.
            *   `[X]` Given the comprehensive shift, this file is expected to be fully deprecated and deleted.
    *   `database/qdrant_connector.py` (Analysis Pending):
        *   `[ ]` **Analyze**:
            *   `[ ]` **Decision**: This is a well-encapsulated Qdrant client wrapper. It should be **[K] Kept** and **[M] Reused/Adapted** by the `Ingestion Orchestration FastAPI App` and future query services. Configuration (host, port) will need to come from environment variables for services (e.g., `localhost` if Qdrant is local/Docker, or a specific host if remote).
    *   `database/vector_db.py` (Analysis Pending):
        *   `[X]` **Analyze**: Determine its role. It might be an abstract DB interface, or specific to another vector DB, or an earlier version of Qdrant interaction. Its fate depends on its content and relevance to the new Qdrant-focused `Database Service`.
            *   `[X]` **Decision**: This file manages a local file-based database (.npy for embeddings, .csv for metadata) and includes logic for building this local DB by directly calling ML model inference functions. 
            *   `[X]` **[D] Deprecate/Delete**: Its functionality is superseded by the new service-based architecture. The `Ingestion Orchestration FastAPI App` will handle the data pipeline, calling the `ML Inference FastAPI App`, and storing data in Qdrant (via the `Database Service`). The local file-based database is being deprecated for Sprint 06 in favor of Qdrant as the primary store. (Deleted)
    *   `database/init.sql/` (Directory):
        *   `[X]` **[D] Delete**: This directory is currently empty and appears to be a remnant, possibly from a previous relational database setup. It is not relevant to the Qdrant-focused architecture for Sprint 06.

10. **UI Screens & Components (`screens/`, `components/`)**
    *   `[ ]` **[K]** For Sprint 06, these are largely untouched as per the PRD's focus on backend services.
    *   **Future Sprints**: They will need to be updated to:
        *   Fetch data from Qdrant (potentially via a new API gateway or backend-for-frontend service that talks to Qdrant).
        *   Trigger actions (like search, AI Guessing Game if it uses embeddings) by calling the relevant services.

11. **Scripts (`scripts/`)**
    *   `scripts/mvp_app.py`:
        *   `[X]` **[U] Role Clarification**: `scripts/batch_processing_client.py` is now the primary client for triggering batch ingestion via the `Ingestion Orchestration FastAPI App`.
        *   `[X]` **[D] Deprecate (Batch Ingestion Logic Only)**: The direct ML model loading, inference, and Qdrant interaction logic within `mvp_app.py` *specifically for batch folder processing* is superseded by the service-based approach initiated by `scripts/batch_processing_client.py`.
        *   `[K]` **[K] Keep (Other Features)**: Other functionalities of `mvp_app.py` (e.g., client-side search, summary/CSV reporting, watch mode for incremental indexing, embedding cache utilities) will be **Kept** for now.
        *   `[ ]` **Future Analysis**: These kept features will be reviewed in a subsequent phase. They may be:
            *   Adapted to work with the new backend services (e.g., search calls an API endpoint).
            *   Migrated into dedicated utility scripts or UI components.
            *   Explicitly deprecated if their functionality is fully covered elsewhere or no longer required.
        *   `[ ]` **No Destruction**: The file `scripts/mvp_app.py` itself will **not** be deleted or destroyed in this sprint as part of the batch ingestion refactor.
    *   `scripts/batch_processing_client.py` (Client for Ingestion):
        *   `[X]` **[U] Primary Ingestion Client**: Confirmed as the client to interact with the `Ingestion Orchestration FastAPI App`.
        *   `[X]` **[U/M]** Adapted with argument parsing for directory input, enhanced error handling, and status display.
        *   `[X]` **[U]** Main workflow makes HTTP API calls to the `Ingestion Orchestration FastAPI App`.
    *   `scripts/upload_to_qdrant.py`:
        *   `[X]` **[D] Deprecate/Delete**: This script uploads pre-existing local `.npy`/`.csv` files to Qdrant. This workflow is superseded by the `Ingestion Orchestration FastAPI App` which handles data generation and direct Qdrant upload. The local file DB format is also deprecated for Sprint 06.
    *   Test scripts (`scripts/test_*.py`):
        *   `[ ]` **[U/D] Review & Refactor/Delete**: Existing test scripts that target components being deprecated/deleted (e.g., tests for `core/optimized_model_manager.py`, `core/background_loader.py`, `database/db_manager.py`, `database/vector_db.py`, old `mvp_app.py` functionality) will need to be reviewed. They should either be deleted or significantly refactored if they can be adapted to test the new client behavior or remaining UI components.
        *   `[ ]` **Note**: New unit and integration tests will be required for the new services (`ML Inference FastAPI App`, `Ingestion Orchestration FastAPI App`) and the refactored `mvp_app.py` client, as per the DoD for those components. This task focuses on the fate of *existing* test scripts.

12. **Utilities (`utils/`)** (Placeholder for future analysis)
    *   `[ ]` Files like `utils/metadata_extractor.py`, `utils/embedding_cache.py`, `utils/incremental_indexer.py`, `utils/logger.py`, `utils/cuda_utils.py` will need to be analyzed. Some might be used by the new services (e.g., `metadata_extractor` by Ingestion Orchestration FastAPI App; `logger` and `cuda_utils` by ML Inference FastAPI App), some refactored, some deprecated if their functionality is absorbed or made obsolete. 