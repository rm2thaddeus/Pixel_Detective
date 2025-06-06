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

4.  **Core Application Stability & Foundational Debugging:**
    *   **Status:** Completed.
    *   **Goal:** Resolve critical application startup failures to unblock all frontend development and testing.
    *   **Details & Implementation Notes:**
        *   **Centralized Logging Utility:**
            *   Enhanced `utils/logger.py` to provide a standardized, configurable, and file-rotating logger for the entire application.
            *   Integrated this logger across all core frontend modules (`app_state.py`, `screen_renderer.py`, `service_api.py`, `background_loader.py`) to provide rich, contextual debug information. Log level is configurable via `LOG_LEVEL` environment variable.
        *   **Resolved Module Import Strategy:**
            *   Systematically refactored all local imports within the `frontend` directory to use a consistent, absolute path from the project root (e.g., `from frontend.core...`).
            *   This resolved persistent `ModuleNotFoundError` and `ImportError` exceptions that were preventing the application from starting.
        *   **Implemented Graceful Error Handling UI:**
            *   Created the missing `frontend/screens/error_screen.py` module.
            *   Implemented `render_error_screen` to provide users with a clear error message and recovery options ("Try Again", "Restart") when a critical frontend exception occurs.
            *   Integrated this error screen into the main application flow in `screen_renderer.py`.

---

## II. Completed Bug Fixes (Post-Stability)

This section details bugs that were identified and fixed after the initial application stability was achieved, unblocking core functionality.

1.  **BUG-09-01: `AttributeError` Crash on Fast UI Screen**
    *   **Status:** Fixed.
    *   **Symptom:** The app loaded but immediately showed an `AttributeError: 'BackgroundLoader' object has no attribute 'start_background_preparation'` on the home screen.
    *   **Analysis:** The `FastUIScreen` was calling an obsolete method (`start_background_preparation`) left over from a previous architecture.
    *   **Resolution:** Removed the obsolete method and its call from `frontend/screens/fast_ui_screen.py`, resolving the crash.

2.  **BUG-09-02: DNG Image Files Not Recognized by Frontend**
    *   **Status:** Fixed.
    *   **Symptom:** When a user selected a folder for ingestion, any `.dng` files within it were ignored.
    *   **Analysis:** The frontend's file discovery logic contained a hardcoded list of image extensions that was missing the `.dng` format.
    *   **Resolution:** Added `.dng` to the set of recognized `image_extensions` in `frontend/screens/fast_ui_screen.py`, allowing them to be discovered and processed.

---

## III. Next Steps & Remaining Tasks

We will break down the work into four phases. Each phase contains detailed, sequential steps with file paths and example commands. Follow each step carefully, and check your work before moving on.

### Phase 1: End-to-End Smoke Testing & Triage

1. **Launch the application**
   - Open a new terminal.
   - Change directory to the frontend folder:
     ```bash
     cd /c:/Users/aitor/OneDrive/Escritorio/Vibe Coding/frontend
     ```
   - Run the Streamlit app:
     ```bash
     streamlit run app.py
     ```
   - Wait for the browser to open and verify that the Fast UI screen (welcome header and folder input) appears without errors.

2. **Select a folder and start ingestion**
   - On the Fast UI screen, click the 📁 **Browse** button and choose a folder containing at least one image (.jpg, .png, .dng).
   - Alternatively, type the full folder path into the text box and press Enter.
   - Verify that the green “Found X+ images” message appears, then click **🚀 Start Building Your Image Search Engine**.
   - Confirm that the app transitions to the loading screen within a few seconds.

3. **Monitor logs and progress**
   - On the loading screen, verify that the progress bar moves and the status message updates.
   - Expand the **Loading Details/Logs** section and confirm you see timestamped log entries.
   - Ensure no unexpected errors (red messages). If errors appear, note the exact error text and file/line references.

4. **Verify Advanced UI transition**
   - After progress reaches 100%, confirm that the **🎉 Loading Complete!** banner appears briefly.
   - The app should automatically switch to the Advanced UI screen.
   - Verify that the search interface loads and is ready for queries.

5. **Document failures**
   - If any of the above steps fail, capture screenshots or copy-paste errors.
   - Create a new GitHub issue or add a note in this file under a “Known Issues” subsection for follow-up.

### Phase 2: Frontend Fixes & UI Restoration

#### A. Fast UI Screen (`frontend/screens/fast_ui_screen.py`)

1. **Re-attach the “Start” trigger**
   - Open `frontend/screens/fast_ui_screen.py`.
   - Locate the button definition:
     ```python
     if st.button("🚀 Start Building Your Image Search Engine", key="start_btn"):
         FastUIScreen._start_processing(folder_path)
     ```
   - Replace the call to `_start_processing` with:
     ```python
     st.session_state.trigger_loading = True
     st.rerun()
     ```
   - Remove or comment out any direct calls to `_start_processing`.

2. **Add a “Merge Folder” button**
   - Immediately below the “Start” button, add:
     ```python
     if st.button("🔄 Merge New Images", key="merge_btn", use_container_width=True):
         st.session_state.merge_folder_path = folder_path
         st.session_state.trigger_merge = True
         st.rerun()
     ```

3. **Prompt for collection existence**
   - In `FastUIScreen.render()` (or `app.py` before screen render), insert:
     ```python
     status = await service_api.get_collection_status()
     if not status.get("exists", False):
         st.warning("Qdrant collection not found. Create a new collection from this folder below.")
     ```
   - Add a text input and **Create Collection** button that sets:
     ```python
     st.session_state.trigger_create = True
     st.session_state.create_folder_path = folder_input_value
     st.rerun()
     ```

#### B. Loading / Progress Screen (`frontend/screens/loading_screen.py`)

1. **Render full log history**
   - Open `frontend/screens/loading_screen.py`.
   - After displaying the progress bar, add:
     ```python
     with st.expander("📜 All Logs", expanded=False):
         all_logs = st.session_state.get("bg_loader_all_logs", [])
         st.text_area("Backend Logs", "\n".join(all_logs), height=200)
     ```
   - In `BackgroundLoader.check_ingestion_status()`, append each new log message into `st.session_state["bg_loader_all_logs"]`.

2. **Display transient polling errors**
   - Wrap the `await background_loader.check_ingestion_status()` call in `render()` with:
     ```python
     try:
         await background_loader.check_ingestion_status()
     except Exception as e:
         st.warning(f"Warning: Failed to fetch status update: {e}")
     ```

3. **Add a “Retry” button on error**
   - In `_handle_completion_or_errors()`, under the error case:
     ```python
     if loader_status == "error":
         if st.button("🔄 Retry Ingestion"):
             await background_loader.start_loading_pipeline(st.session_state.folder_path)
         return
     ```

#### C. Contextual Sidebar (`frontend/components/sidebar/context_sidebar.py`)

1. **Expander for full logs**
   - In the sidebar render function, after the status indicator:
     ```python
     with st.expander("📜 Show All Logs"):
         logs = st.session_state.get("bg_loader_all_logs", [])
         st.text("\n".join(logs))
     ```

2. **Re-add Merge UI**
   - If `st.session_state.database_built` is `True`, add:
     ```python
     if st.button("🔄 Merge Additional Images", use_container_width=True):
         st.session_state.merge_folder_path = st.session_state.folder_path
         st.session_state.trigger_merge = True
         st.rerun()
     ```

### Phase 3: Service-API & Backend Endpoint Work

#### A. Extend `frontend/core/service_api.py`

Add these async functions at the bottom of the file:
```python
async def get_collection_status():
    response = await get_async_client().get(
        f"{INGESTION_ORCHESTRATION_URL}/collection/status"
    )
    response.raise_for_status()
    return response.json()

async def create_collection(directory_path: str):
    return await get_async_client().post(
        f"{INGESTION_ORCHESTRATION_URL}/collection/create",
        json={"directory_path": directory_path},
    )

async def merge_folder(directory_path: str):
    return await get_async_client().post(
        f"{INGESTION_ORCHESTRATION_URL}/ingest/merge",
        json={"directory_path": directory_path},
    )
```

#### B. New FastAPI Routes (`backend/ingestion_orchestration_fastapi_app/main.py`)

1. **GET /api/v1/collection/status**
    ```python
    @v1_router.get("/collection/status")
    async def collection_status(
        q_client: QdrantClient = Depends(get_qdrant_dependency)
    ):
        exists = await q_client.has_collection(QDRANT_COLLECTION_NAME)
        return {"exists": exists}
    ```

2. **POST /api/v1/collection/create**
    - Mirror `/ingest` logic but force creation of a new collection.

3. **POST /api/v1/ingest/merge**
    - Add a new endpoint that calls `_run_ingestion_task` with a merge flag.

#### C. (Optional) Persistent Job State Storage

- Consider replacing the in-memory `job_status_db` with DiskCache or Redis so job progress survives service restarts.

### Phase 4: Testing & Documentation

1. **Unit & Integration Tests**
   - Create pytest tests under `backend/tests/` for:
     - `/collection/status`
     - `/collection/create`
     - `/ingest/merge`
   - Use `pytest-asyncio` to mock FastAPI dependencies and Qdrant client.

2. **Playwright E2E Tests**
   - In `frontend/tests/playwright/`, automate the main user flow:
     1. Launch the app.
     2. Select a folder.
     3. Click "Start".
     4. Wait for Advanced UI screen.

3. **Documentation Updates**
   - Update `docs/sprints/sprint-09/PRD.md` in the "Requirements Matrix" and "Technical Architecture" sections.
   - Add a new entry in `docs/CHANGELOG.md` summarizing:
     - Restored Fast UI triggers
     - Added Merge endpoint and UI
     - Extended service API
     - Full logs in UI