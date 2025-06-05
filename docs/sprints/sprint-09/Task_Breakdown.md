# Sprint 09 Task Breakdown

**Overall Sprint Goal:** Restore all core user flows (especially "Folder Load"), ensure API-driven architecture is stable, and improve error handling and test coverage, with a specific focus on providing real-time progress and log updates from the backend to the frontend sidebar.

---

## I. Completed Tasks (Frontend Foundation for Logging Integration)

This section details the foundational work done on the frontend to prepare for receiving and displaying backend logs and progress for ingestion tasks.

1.  **`frontend/core/background_loader.py` Refinements:**
    *   **Status:** Modified and user-accepted.
    *   **Changes:**
        *   Ensured `job_id` received from `service_api.ingest_directory` is correctly stored in `st.session_state[LOADING_JOB_ID_KEY]`.
        *   The loader now fetches job status/details via `service_api.get_ingestion_status(job_id)`.
        *   **Adapted to backend API change:** It now expects logs in an array `api_response.get("logs")` and joins them into a newline-separated string for `st.session_state[LOADING_DETAIL_KEY]`. Falls back to `message` or `details` fields if `logs` is not present.

2.  **`frontend/components/sidebar/context_sidebar.py` Major Refactor:**
    *   **Status:** Modified and user-accepted.
    *   **Changes:**
        *   `render_sidebar` function converted to `async def`.
        *   Now uses the global `background_loader` instance to initiate folder ingestion tasks.
        *   Displays dynamic status, progress percentage, and error messages derived from `background_loader.progress` properties.
        *   Includes an `st.expander("Show Details/Logs")` that will display the content of `background_loader.progress.current_detail` (intended to be the logs from the backend).
        *   Periodically calls `await background_loader.check_ingestion_status()` within its render cycle if a job is active, to refresh the status and logs.
        *   Temporarily removed the "Merge Folder" UI to focus on the primary ingestion log display, as `background_loader` currently handles one job at a time.

3.  **Adaptation of Calling Hierarchy for `async` Sidebar:**
    *   **Status:** Verified and user-accepted changes in relevant files.
    *   **`frontend/screens/advanced_ui_screen.py`:**
        *   The method `_render_contextual_sidebar` (which calls `render_sidebar`) was converted to `async def`.
        *   The call to `render_sidebar()` within it is now `await render_sidebar()`.
        *   The call to `AdvancedUIScreen._render_contextual_sidebar()` from `AdvancedUIScreen.render()` is now `await AdvancedUIScreen._render_contextual_sidebar()`.
        *   The necessary import `from frontend.components.sidebar.context_sidebar import render_sidebar` has been added.
    *   **`frontend/core/screen_renderer.py`:**
        *   The main `render_app` function (which is `ScreenRenderer.render`) is already `async`.
        *   `AdvancedUIScreen.render()` (which calls the sidebar) is correctly `await`ed within `render_app`.
    *   **`frontend/app.py`:**
        *   The main application entry point `main_async()` is already `async` and uses `asyncio.run()`, correctly handling the `async` rendering chain.

---

## II. Remaining Tasks to Complete Sprint 09

This section outlines the necessary backend development, final frontend integration touches, and testing required to complete the logging feature and other sprint goals.

### A. Backend API and Logging Enhancements (Ingestion Service)

> **Note:** Qdrant collections can become corrupted (e.g., due to abrupt shutdowns or disk issues). For development, manual reset is acceptable, but for production/scale-up, a failsafe mechanism should be implemented: regular automated backups, health checks, and automated restore/recovery scripts.

1.  **Task: Implement Real Job Management & Background Processing for Ingestion**
    *   **Status:** Substantially complete.
    *   **Goal:** `/api/v1/ingest/` endpoint should initiate folder ingestion as a non-blocking background task and return a `job_id`.
    *   **Details & Implementation Notes:**
        *   Modified `ingest_directory_v1` in `backend/ingestion_orchestration_fastapi_app/main.py` to use FastAPI's `BackgroundTasks`.
        *   Generates a unique `job_id` for each ingestion request.
        *   Initial job status (e.g., "pending", progress, initial log) is stored in the in-memory `job_status_db`.
        *   The core ingestion logic moved to `_run_ingestion_task` and scheduled in the background.
        *   The endpoint now immediately returns the `job_id` and initial status.

2.  **Task: Implement Persistent Job State Storage (Status, Progress, Logs)**
    *   **Status:** Partially complete (in-memory storage implemented).
    *   **Goal:** Store status, progress percentage, and detailed log messages for each ingestion job.
    *   **Details & Implementation Notes:**
        *   An in-memory dictionary `job_status_db` in `backend/ingestion_orchestration_fastapi_app/main.py` is used for job state.
        *   The background ingestion task (`_run_ingestion_task`) updates this store with:
            *   Current status (e.g., "processing", "completed", "failed").
            *   Progress percentage.
            *   A list of log messages (strings) detailing its operations and any errors, using the `log_to_job` helper.
        *   *Consideration for future sprints: For production, replace in-memory storage with a more robust solution like Redis if service instances might be restarted or scaled.*

3.  **Task: Enhance Ingestion Task Logging**
    *   **Status:** Substantially complete.
    *   **Goal:** The ingestion background task should capture detailed operational logs.
    *   **Details & Implementation Notes:**
        *   The `_run_ingestion_task` and its helper `process_batch_with_ml_service` in `backend/ingestion_orchestration_fastapi_app/main.py` now use the `log_to_job` helper.
        *   Log messages (timestamped and with level) are collected in `job_status_db[job_id]["logs"]`.

4.  **Task: Update `/ingest/status/{job_id}` Endpoint for Real Data**
    *   **Status:** Substantially complete.
    *   **Goal:** `/api/v1/ingest/status/{job_id}` endpoint should return actual status, progress, and detailed logs.
    *   **Details & Implementation Notes:**
        *   Modified `get_ingestion_status_v1` in `backend/ingestion_orchestration_fastapi_app/main.py` to retrieve job information from `job_status_db`.
        *   Populates the `JobStatusResponse` model, which now returns `logs: List[str]` containing the collected log messages. Other fields include `status`, `progress`, `result`, `directory_path`, and `total_files`.
        *   Handles cases where the `job_id` is not found (returns 404).

### B. Frontend Polish & Final Integration

1.  **Task: Adapt Frontend Log Display (If Necessary)**
    *   **Status:** Complete.
    *   **Goal:** Ensure logs from the backend are displayed clearly in the sidebar.
    *   **Details & Implementation Notes:**
        *   `frontend/core/background_loader.py` (in `check_ingestion_status`) was updated to expect logs from `api_response.get("logs")` (a list of strings). It joins this list into a newline-separated string for display in the sidebar via `st.session_state[LOADING_DETAIL_KEY]`.

### C. Restore and Test Other Core User Flows (As per Sprint Plan)

*(Refer to `transition-to-sprint-09.md` for full details on these tasks. Focus now shifts heavily to testing and validation of the folder load and logging feature.)*

1.  **TASK-09-01:** Restore "Folder Load" functionality (UI → API → backend).
    *   **Status:** Backend and frontend plumbing is largely in place. Requires thorough end-to-end testing.
    *   Ensure user feedback for errors (now enhanced with detailed logs).
    *   Add/verify integration tests for this flow.
2.  **TASK-09-02:** Expand integration tests for all major user flows (search, duplicate detection, random image, filtering).
3.  **TASK-09-03:** Ensure all API endpoints are covered by unit and integration tests (especially the new job status and ingestion flow).
4.  **TASK-09-04:** Add robust error handling and user feedback for all critical UI actions (detailed logs in sidebar contribute significantly).

### D. Medium & Low Priority Tasks

*(Refer to `transition-to-sprint-09.md`)*
-   **TASK-09-05:** Performance benchmarking (especially for ingestion).
-   **TASK-09-06:** UI polish and bug fixes identified during testing.
-   **TASK-09-07:** Documentation updates (API docs for new job endpoints, architecture diagrams if changed).
-   **TASK-09-08:** Cleanup of legacy modules.

---

This breakdown should serve as a clear checklist for completing Sprint 09. 