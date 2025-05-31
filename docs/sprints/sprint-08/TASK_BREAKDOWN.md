# Sprint 08 Task Breakdown

## Objective 1: Qdrant Integration (Backend)
- [ ] TASK-08-01-01: Spike Qdrant Python client setup and connectivity test.
- [ ] TASK-08-01-02: Implement `/api/v1/search` endpoint with vector and attribute filters.
- [ ] TASK-08-01-03: Implement `/api/v1/images` endpoint with pagination, filtering, and sorting.
- [ ] TASK-08-01-04: Write unit tests for search and images endpoints.

## Objective 2: Duplicate Detection Feature
- [ ] TASK-08-02-01: Design and document `/api/v1/duplicates` endpoint in OpenAPI.
- [ ] TASK-08-02-02: Implement duplicate detection algorithm using Qdrant vector similarity and `ThreadPoolExecutor`.
- [ ] TASK-08-02-03: Expose duplicate task in `service_api.py` with background thread and `st.spinner` integration.
- [ ] TASK-08-02-04: Build Streamlit UI: Duplicate Detection Tab with placeholders, progress bar, and results table.
- [ ] TASK-08-02-05: Develop integration tests for duplicate detection flow.

## Objective 3: Random Image Selection
- [ ] TASK-08-03-01: Define `/api/v1/random` endpoint schema and documentation.
- [ ] TASK-08-03-02: Implement random image selection logic in FastAPI.
- [ ] TASK-08-03-03: Add `get_random_image` method to `service_api.py` using `httpx.AsyncClient`.
- [ ] TASK-08-03-04: Create Streamlit UI component: Random Image Selector with `st.empty()` placeholder.
- [ ] TASK-08-03-05: Write unit and integration tests for random endpoint and UI component.

## Objective 4: Advanced Filtering & Sorting UI
- [ ] TASK-08-04-01: Extend `service_api.py` methods to accept filter and sort query parameters.
- [ ] TASK-08-04-02: Implement Streamlit UI controls: `st.multiselect` for tags, `st.slider` for date range, `st.radio` for sort order.
- [ ] TASK-08-04-03: Cache filter options with `@st.cache_data` to reduce API calls.
- [ ] TASK-08-04-04: Write tests for filter logic and UI behavior under edge cases.

## Objective 5: Error Handling & UI Polish
- [ ] TASK-08-05-01: Add FastAPI exception handlers for standardized error responses (422, 500).
- [ ] TASK-08-05-02: Implement UI error banners in Streamlit using `st.error` with retry buttons.
- [ ] TASK-08-05-03: Incorporate skeleton/loading states via `st.empty`, `st.spinner`, and `st.progress` during API calls.
- [ ] TASK-08-05-04: Conduct accessibility audit on new components (ARIA labels, keyboard navigation).

## Objective 6: Testing & Stability
- [ ] TASK-08-06-01: Expand integration tests for full UI → API → Qdrant roundtrip using Docker Compose.
- [ ] TASK-08-06-02: Develop end-to-end tests with Playwright for critical user flows (search, duplicates, random).
- [ ] TASK-08-06-03: Add negative tests for invalid parameters and no-data scenarios.
- [ ] TASK-08-06-04: Benchmark performance of key endpoints with `pytest-benchmark` and analyze with `nsys`.

## Objective 7: Documentation & Cleanup
- [ ] TASK-08-07-01: Update `service_api.py` docstrings and generate code examples in `/docs/api/service_api.md`.
- [ ] TASK-08-07-02: Refresh architecture diagrams in `/docs/architecture.md` to include Qdrant and new endpoints.
- [ ] TASK-08-07-03: Write a developer guide (`/docs/developers/feature_extension.md`) for search and filter extension.
- [ ] TASK-08-07-04: Update `CHANGELOG.md` with Sprint 08 feature and fix entries.
- [ ] TASK-08-07-05: Deprecate legacy modules: remove `core/fast_startup_manager.py` and `utils/embedding_cache.py` after ensuring no references. 