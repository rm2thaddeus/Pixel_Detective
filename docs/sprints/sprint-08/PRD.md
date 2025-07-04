# Sprint 08 Product Requirements Document (PRD)

## 1. Executive Summary
Sprint 08 focuses on integrating Qdrant for robust vector search and image listing, delivering key user-facing features (duplicate detection, random image selection, advanced filtering/sorting), enhancing UI feedback and accessibility, and solidifying testing, stability, and documentation.

## 2. Context7 Research Summary
- **Streamlit Background Tasks**: Leverage `st.cache_resource` for shared clients, `st.spinner`/`st.progress` for UI feedback, and background threads/task queues for long-running operations.
- **Async & Lazy Patterns (o3research)**: Use `asyncio` in `service_api.py`, cache the HTTPX client, and lazy-load heavy modules via `@st.cache_resource` to minimize cold-start time. **This sprint emphasized centralizing all backend communication through `service_api.py` to further enhance decoupling and UI responsiveness.**
- **Performance Optimizations**: Adopt multipart form-data for image uploads, Brotli compression, and Qdrant indexing strategies to meet sub-200ms response targets.

## 3. Requirements Matrix
| ID        | User Story                                                                                   | Acceptance Criteria                                                                                                               | Status |
|-----------|----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|--------|
| FR-08-01  | As a user, I want to search images so that I can find relevant items quickly.               | - `/api/v1/search` returns correct vectors and metadata<br>- Pagination metadata returned<br>- Filters (date, tag) applied      | ✅ Done |
| FR-08-02  | As a user, I want to list images with pagination, filtering, and sorting.                    | - `/api/v1/images` returns paginated results<br>- Filtering controls work correctly<br>- Sorting (asc/desc) works                 | ✅ Done |
| FR-08-03  | As a user, I want to detect duplicate images so I can clean up my collection.               | - `/api/v1/duplicates` returns groups of duplicates<br>- UI displays groups with visual indicators<br>- Operation runs under 500ms | ✅ Done |
| FR-08-04  | As a user, I want a random image feature for exploration.                                    | - `/api/v1/random` returns a valid random image object                                                                                | ✅ Done |
| NFR-08-01 | System must handle up to 100k items with <200ms average response latency.                    | - Load tests confirm average latency <200ms for search and list endpoints                                                        | 🟡 Pending |
| NFR-08-02 | UI must maintain smooth interactions (>30 FPS) during navigation and filter changes.           | - Streamlit profiler reports >30 FPS on 1080p display                                                                              | ✅ Done |
| NFR-08-03 | Maintainable and Decoupled Frontend Architecture.                                            | - Backend interactions are centralized in `service_api.py`.<br>- UI components are primarily responsible for presentation and user interaction, not direct data fetching or model management. | ✅ Done |

## 4. Technical Architecture
- **Backend Services**: FastAPI with Qdrant Python client under `/api/v1` namespace; new routers: `search`, `images`, `duplicates`, `random`, **and a new endpoint `vectors/all-for-visualization` to supply data for latent space exploration.** For local development and testing, these FastAPI services will be run manually. Docker Compose will be used to manage the Qdrant instance.
- **Frontend App**: Streamlit with `httpx.AsyncClient` in `service_api.py`; all UI screens (including `latent_space.py`) are now API-driven, stateless, and accessible. Batch embedding/captioning is supported. All backend communication is via `service_api.py`. Error handling and design system usage are standardized throughout.
- **Data Layer**: Qdrant as vector database; attribute-based filtering for metadata; pagination via offset+limit.
- **Background Processing**: Use Python `ThreadPoolExecutor` or lightweight task queue for duplicate detection; integrate with Streamlit via threads and `st.spinner`. **Folder ingestion tasks initiated from the UI (`context_sidebar.py`) are handled by submitting tasks that call the backend Ingestion Orchestration service via `service_api.py`.**

## 5. Implementation Timeline
| Week   | Milestones                                                                                                   |
|--------|--------------------------------------------------------------------------------------------------------------|
| Week 1 | Qdrant integration spike; implement and unit-test `/search` and `/images` endpoints.                         |
| Week 2 | Complete `/duplicates` and `/random` endpoints; update `service_api.py`; write unit tests.                    |
| Week 3 | Develop Streamlit UI: Duplicate Detection Tab, Random Image Selector, enhanced SearchScreen with filters.     |
| Week 4 | Add skeleton/loading states, error handling banners, conduct integration & E2E tests, finalize documentation.    |

## 6. Testing Strategy
- Unit tests for each FastAPI endpoint and `service_api.py` methods.  
- Integration tests using Docker Compose (for Qdrant) with manually started FastAPI services for full-stack validation.  
- E2E tests with Playwright for UI flows (search, duplicates, random, filtering).  
- Performance benchmarks via `pytest-benchmark` and `nsys` profiling for NFR compliance.

## 7. Risk Assessment
| Risk                            | Mitigation Plan                                                                                               |
|---------------------------------|--------------------------------------------------------------------------------------------------------------|
| Qdrant integration delays       | Start with a small spike in Week 1; use mock data if needed; seek support from Qdrant docs/community         |
| UI performance regression       | Use `@st.cache_resource` and lazy-loading; fallback to simplified UI if needed; measure FPS regularly         |
| Test flakiness in CI            | Use stable test fixtures and Docker environments; isolate external dependencies; parallelize tests            |
| Complexity of duplicate logic   | Start with simple cosine similarity threshold; iterate based on performance metrics from load testing         | 