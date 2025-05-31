# Sprint 07 Backlog

This backlog captures all known improvements, technical debt, and follow-up tasks identified during Sprint 07 that were not completed or are deferred for future work.

---

## UI (Frontend)
- [ ] **Duplicate Detection Tab:** Implement UI logic to display and manage duplicates once backend endpoint is available.
- [ ] **Random Image Selection:** Add support for random image selection in AI Game and other features (pending backend support).
- [ ] **Advanced Filtering & Sorting:** Add UI controls for advanced search filtering, sorting, and pagination (pending backend API support).
- [x] **Async Refactor:** Frontend (`service_api.py`, `app.py`, `screen_renderer.py`, screen modules, `background_loader.py`) refactored to use `httpx.AsyncClient` and asynchronous operations for API calls. `httpx` added to `frontend/requirements.txt`.
- [ ] **Error Handling:** Improve user-facing error messages and fallback UI for all API failures and edge cases.
- [ ] **UI Polish:** Further refine design system, accessibility, and responsiveness across all screens.
- [x] **Component Refactor:** Ensure all components (e.g., guessing game, latent space) are fully decoupled and use `service_api` exclusively. (Largely done, service_api is the sole point of backend contact, now async).
- [ ] **Loading/Progress Feedback:** Enhance progress indicators and skeleton screens for all long-running operations (Partially improved with async loading screen updates).
- [ ] **Session State Cleanup:** Audit and clean up any remaining session state keys or logic that reference deprecated local state.

## Backend (FastAPI Services)
- [ ] **Duplicate Detection Endpoint:** Implement and document an endpoint for finding and managing duplicate images.
- [ ] **Random Image Endpoint:** Add an endpoint to fetch a random image from the collection.
- [ ] **Advanced Search/Filtering:** Add support for advanced search, filtering, and sorting in API endpoints.
- [ ] **Pagination:** Ensure all list endpoints support robust pagination and metadata.
- [ ] **Error Details:** Standardize error responses and include helpful error details for all endpoints.
- [x] **CORS:** Ensure CORS middleware is enabled and properly configured for all FastAPI services. (Marked as done in S07 plan).
- [ ] **API Documentation:** Update OpenAPI/Swagger docs to reflect all new and planned endpoints.
- [x] **Fix ingestion pipeline connection:** Frontend `service_api.py` updated to use port 8002.

## Testing & Stability
- [ ] **Integration Tests:** Add/expand integration tests for UI → FastAPI → Qdrant/ML → UI round-trips.
- [ ] **E2E Tests:** Develop end-to-end tests for the full ingestion and search pipeline.
- [ ] **Error Handling Tests:** Add tests for error and edge-case handling in both UI and backend.
- [ ] **Performance Testing:** Benchmark and optimize API and UI performance for large collections.

## Legacy Code & Cleanup
- [ ] **Legacy Module Removal:** Continue deprecating and removing legacy modules as per S06/S07 plans (e.g., core/fast_startup_manager.py, utils/embedding_cache.py, etc.).
- [ ] **MVP App Refactor:** Refactor or remove any remaining features in scripts/mvp_app.py that do not use the new service architecture.
- [ ] **Codebase Audit:** Audit for any remaining direct model/DB calls or deprecated patterns.

## Documentation
- [ ] **API Layer Docs:** Document the service_api layer and its usage in the UI.
- [ ] **Architecture Diagrams:** Update/expand architecture diagrams to reflect the new decoupled structure.
- [ ] **User/Dev Guides:** Add or update guides for running, developing, and extending the new UI and backend services.
- [ ] **Changelog:** Summarize all major changes and migration steps in the project changelog.

---

**Note:** This backlog should be reviewed and prioritized at the start of the next sprint. Items may be split, merged, or re-scoped as needed based on team priorities and new discoveries. 