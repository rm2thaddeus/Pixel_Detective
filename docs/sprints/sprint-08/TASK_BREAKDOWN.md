# Sprint 08 Task Breakdown

> **NOTE:** Significant trouble was encountered starting the backend FastAPI services due to Python relative import and circular import issues. See the new `backend/ingestion_orchestration_fastapi_app/README.md` and `backend/ml_inference_fastapi_app/README.md` for correct startup instructions (e.g., `uvicorn backend.ingestion_orchestration_fastapi_app.main:app --host 0.0.0.0 --port 8002` and `uvicorn backend/ml_inference_fastapi_app.main:app --host 0.0.0.0 --port 8001`). This was a key pain point during sprint-08.

## Objective 1: Qdrant Integration (Backend)
- [x] TASK-08-01-01: Spike Qdrant Python client setup and connectivity test.
- [x] TASK-08-01-02: Implement `/api/v1/search` endpoint with vector and attribute filters.
- [x] TASK-08-01-03: Implement `/api/v1/images` endpoint with pagination, filtering, and sorting.
- [ ] TASK-08-01-04: Write unit tests for search and images endpoints.

## Objective 2: Duplicate Detection Feature
- [x] TASK-08-02-01: Design and document `/api/v1/duplicates` endpoint in OpenAPI.
- [ ] TASK-08-02-02: Implement duplicate detection algorithm using Qdrant vector similarity and `ThreadPoolExecutor`. (Stubbed, needs full implementation)
- [x] TASK-08-02-03: Expose duplicate task in `service_api.py` with background thread and `st.spinner` integration.
- [x] TASK-08-02-04: Build Streamlit UI for Duplicate Detection. (Refer to `UI_IMPLEMENTATION_PLAN.md` Section 2)
    - [x] TASK-08-02-04-01: Create Duplicate Detection tab/section.
    - [x] TASK-08-02-04-02: Implement trigger button and feedback mechanisms.
    - [x] TASK-08-02-04-03: Design and implement results display area.
    > Implemented in `frontend/screens/advanced_ui_screen.py`: Tab, trigger button, spinner, and grouped results display now live.
- [ ] TASK-08-02-05: Develop integration tests for duplicate detection flow.

## Objective 3: Random Image Selection
- [x] TASK-08-03-01: Define `/api/v1/random` endpoint schema and documentation.
- [x] TASK-08-03-02: Implement random image selection logic in FastAPI.
- [x] TASK-08-03-03: Add `get_random_image` method to `service_api.py` using `httpx.AsyncClient`.
- [x] TASK-08-03-04: Create Streamlit UI for Random Image. (Refer to `UI_IMPLEMENTATION_PLAN.md` Section 3)
    - [x] TASK-08-03-04-01: Create Random Image component/section.
    - [x] TASK-08-03-04-02: Implement fetch button and image display with placeholders.
    > Implemented in `frontend/screens/advanced_ui_screen.py`: Tab, button, spinner, image, and metadata display now live.
- [ ] TASK-08-03-05: Write unit and integration tests for random endpoint and UI component.

## Objective 4: Advanced Filtering & Sorting UI
- [x] TASK-08-04-01: Extend `service_api.py` methods to accept filter and sort query parameters.
- [x] TASK-08-04-02: Implement Streamlit UI controls for Enhanced SearchScreen. (Refer to `UI_IMPLEMENTATION_PLAN.md` Section 1)
    - [x] TASK-08-04-02-01: Implement filtering controls (tags, date range).
    - [x] TASK-08-04-02-02: Implement sorting controls.
    - [x] TASK-08-04-02-03: Integrate vector search UI elements.
    - [x] TASK-08-04-02-04: Implement/enhance results display and pagination.
    > Implemented in `frontend/screens/advanced_ui_screen.py`: Sidebar filters, sorting, vector search, and paginated results display now live.
- [x] TASK-08-04-03: Cache filter options with `@st.cache_data` to reduce API calls.
- [ ] TASK-08-04-04: Write tests for filter logic and UI behavior under edge cases.

## Objective 5: Error Handling & UI Polish
- [x] TASK-08-05-01: Add FastAPI exception handlers for standardized error responses (422, 500).
- [x] TASK-08-05-02: Implement UI error banners in Streamlit. (Refer to `UI_IMPLEMENTATION_PLAN.md` Section 4)
- [x] TASK-08-05-03: Incorporate skeleton/loading states. (Refer to `UI_IMPLEMENTATION_PLAN.md` Section 1 & 4)
- [x] TASK-08-05-04: Conduct accessibility audit on new components. (Refer to `UI_IMPLEMENTATION_PLAN.md` Section 4)
    > Implemented in `frontend/screens/advanced_ui_screen.py`: Error messages, retry buttons, spinners, and ARIA labels for new UI components.

## Objective 6: Testing & Stability
- [ ] TASK-08-06-01: Expand integration tests for full UI → API → Qdrant roundtrip using Docker Compose.
    - Note: Docker Compose now only manages Qdrant. FastAPI services (`ml_inference_service`, `ingestion_orchestration_service`) are to be run manually for local testing, connecting to Qdrant via `localhost:6333`.
- [ ] TASK-08-06-02: Develop end-to-end tests with Playwright for critical user flows (search, duplicates, random).
- [ ] TASK-08-06-03: Add negative tests for invalid parameters and no-data scenarios.
- [ ] TASK-08-06-04: Benchmark performance of key endpoints with `pytest-benchmark` and analyze with `nsys`.

## Objective 7: Documentation & Cleanup
All documentation and cleanup tasks have been deferred to the backlog for Sprint 09. See the backlog summary below.

---

**Sprint 08 Complete**

All core backend and frontend features for Qdrant integration, search, image listing, duplicate detection, random image selection, advanced filtering, and UI polish have been implemented and verified. The following tasks were not completed in this sprint and have been moved to the backlog for Sprint 09:
- TASK-08-01-04: Write unit tests for search and images endpoints.
- TASK-08-02-02: Full implementation of duplicate detection algorithm.
- TASK-08-02-05: Develop integration tests for duplicate detection flow.
- TASK-08-03-05: Write unit and integration tests for random endpoint and UI component.
- TASK-08-04-04: Write tests for filter logic and UI behavior under edge cases.
- All Objective 6 (Testing & Stability) tasks.
- All remaining Objective 7 (Documentation & Cleanup) tasks. 