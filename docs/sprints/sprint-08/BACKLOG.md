# Sprint 08 Backlog

This backlog captures all Sprint 07 carry-over tasks and new feature requests for Sprint 08.

---

## High Priority
- 🔹 Qdrant Integration: Replace placeholder search and list endpoints (`/api/v1/search`, `/api/v1/images`).
- 🔹 Duplicate Detection: Backend endpoint and UI tab.
- 🔹 Random Image: Backend endpoint and UI selector.
- 🔹 Advanced Filtering & Sorting: UI controls and backend support.
- 🔹 Pagination: Add robust pagination to `/images` endpoint and UI.
- ✅ **Frontend Refactor & UI Polish: All UI screens (including latent_space.py) are now API-driven, stateless, accessible, and use the design system. Error handling and feedback are standardized.**

## Medium Priority
- 🔸 Error Handling: Improved error messages, standardized responses, retry mechanisms. **(Core work complete; further polish/testing can be addressed as needed.)**
- 🔸 UI Polish: Design refinements, accessibility compliance, responsive layouts. **(Core work complete; further polish/testing can be addressed as needed.)**
- 🔸 Loading/Progress Feedback: Skeleton screens, `st.spinner`, `st.progress` placeholders. **(Core work complete.)**
- 🔸 Session State Cleanup: Audit and remove deprecated `st.session_state` keys.
- 🔸 Docker Strategy Update: For local development/testing, Docker Compose will now primarily manage Qdrant. FastAPI services (ML inference, Ingestion orchestration) will be run manually. This simplifies local setup while ensuring services can communicate via localhost/network.

## Low Priority
- ⚪ Legacy Module Removal: Deprecate and remove `core/fast_startup_manager.py` and `utils/embedding_cache.py`.
- ⚪ MVP App Refactor: Clean up or remove `scripts/mvp_app.py` features not using service_api.
- ⚪ Performance Testing: Benchmark with realistic large datasets and optimize if needed.
- ⚪ E2E Tests: Develop additional end-to-end tests for complex user flows.
- ⚪ API Documentation: Auto-generate Swagger/OpenAPI docs for new endpoints.
- ⚪ Architecture Diagrams Update: Refresh diagrams in `/docs/architecture.md`.

---

**Note**: Prioritize high-priority items in Weeks 1–2, then address medium items in Week 3, and low priority as time allows in Week 4. 