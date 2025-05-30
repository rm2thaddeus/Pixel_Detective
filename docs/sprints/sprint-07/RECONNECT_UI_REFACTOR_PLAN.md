# Sprint 07 Refactoring Plan: Reconnecting the UI to Service-Oriented Backend & Frontend Folderization

This document outlines the steps and components affected by the transition to a fully decoupled architecture, where the Streamlit UI is reconnected to backend services (ML Inference and Ingestion Orchestration FastAPI apps), and all Streamlit-related code is moved into a dedicated `frontend/` folder.

**Legend:**
*   **[C] Create**: New component/folder/service.
*   **[M] Migrate**: Existing logic to be moved/refactored.
*   **[U] Update**: Existing component to interact with new services or structure.
*   **[D] Deprecate/Delete**: Logic/component to be removed after migration.
*   **[K] Keep**: Component largely unchanged but may need minor adjustments.

---

## Overall Architecture Goal

*   **Frontend (Streamlit UI)**: All UI logic and Streamlit code lives in `frontend/`. The UI interacts with backend services only via HTTP API calls.
*   **Backend Services**: ML Inference and Ingestion Orchestration FastAPI apps, and Qdrant (DB), as already implemented.
*   **No direct model/database calls in UI**: All such logic is replaced by API calls.

---

## Phase 1: Frontend Folderization & Initial Migration

1.  **[C] Create `frontend/` Folder**
    *   Move `app.py`, `core/`, `screens/`, `components/`, and any other Streamlit-specific files into `frontend/`.
    *   Update all import paths as needed (e.g., `from core.screen_renderer` → `from frontend.core.screen_renderer`).
    *   Update documentation and README to reflect new structure.

2.  **[M] Migrate Streamlit Entry Point**
    *   Move `app.py` to `frontend/app.py`.
    *   Update any scripts or deployment configs to launch Streamlit from `frontend/app.py`.

3.  **[U] Update Requirements**
    *   Create `frontend/requirements.txt` with all Streamlit and UI dependencies.
    *   Remove Streamlit and UI dependencies from backend service requirements.

---

## Phase 2: Decoupling UI from Local Model/DB Logic

4.  **[D] Deprecate/Delete Direct Model/DB Calls in UI**
    *   Remove all direct imports and usage of `core/optimized_model_manager.py`, `models/clip_model.py`, `models/blip_model.py`, and any local Qdrant/database logic from UI code.
    *   Remove or refactor any caching or state logic that assumed local model access.

5.  **[C] Create `frontend/core/service_api.py`**
    *   Implement a service API layer that wraps all HTTP calls to backend services.
    *   Example functions:
        *   `get_embedding(image_bytes)`
        *   `get_caption(image_bytes)`
        *   `ingest_directory(path)`
        *   `get_ingestion_status(job_id)`
        *   `search_images(query)`
    *   Use the `requests` library for synchronous calls (or `httpx` if async is needed).
    *   Make backend URLs configurable via environment variables or a config file.

6.  **[U] Update UI Screens and Components**
    *   In `core/screen_renderer.py` and all screen/component modules:
        *   Replace any logic that previously called local model/database functions with calls to the new `service_api.py` functions.
        *   Handle loading, error, and result states based on API responses.
        *   Show progress/status by polling the backend if needed (e.g., for long-running ingestion).
    *   Use the reference guides in `docs/reference_guides/` to inform UX and flow.

7.  **[U] Update State Management**
    *   Refactor any state management (e.g., `core/app_state.py`) to work with data from backend services, not local state.
    *   Remove or refactor any logic that assumed local model loading or direct DB access.

---

## Phase 3: Backend Service Adjustments (if needed)

8.  **[U] Add/Adjust FastAPI Endpoints**
    *   Review UI requirements and add any missing endpoints to the ML Inference or Ingestion Orchestration FastAPI apps.
    *   Ensure endpoints return all data needed by the UI (e.g., status, results, error details).
    *   Add CORS middleware to FastAPI apps to allow requests from the Streamlit frontend.

---

## Phase 4: Testing & Documentation

9.  **[C] Create/Update Integration Tests**
    *   Add tests to verify end-to-end flow: UI → FastAPI → Qdrant/ML → UI.
    *   Test error handling, loading states, and edge cases.

10. **[U] Update Documentation**
    *   Update all relevant docs (README, reference guides, sprint docs) to reflect the new architecture and UI-backend interaction model.
    *   Document the new API layer and how UI components interact with it.

---

## Migration Notes

*   All Streamlit/UI code is now in `frontend/`.
*   The UI is fully decoupled from backend logic—no direct model or DB calls.
*   All communication between UI and backend is via HTTP API calls.
*   Reference guides in `docs/reference_guides/` should be used to refine UX and flow.
*   The backend services (ML Inference, Ingestion Orchestration, Qdrant) remain unchanged except for possible endpoint additions or CORS config.

---

## Checklist

- [ ] Create `frontend/` folder and move all UI code
- [ ] Update import paths and requirements
- [ ] Remove all direct model/DB calls from UI
- [ ] Implement `service_api.py` for backend communication
- [ ] Refactor UI screens/components to use API layer
- [ ] Update state management for service-based data
- [ ] Add/adjust FastAPI endpoints as needed
- [ ] Add CORS to FastAPI apps
- [ ] Test end-to-end flow
- [ ] Update documentation and guides 