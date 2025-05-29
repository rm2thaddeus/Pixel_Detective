# Sprint 05 Technical Implementation Plan: UX Flow, UI Screens, and Performance

**Objective:** Implement the core UX flow (FAST_UI, LOADING, ADVANCED_UI), resolve the BLIP model captioning issue, and significantly optimize application startup performance by deferring heavy imports and leveraging background loading.

## Goals

-   Implement `screens/fast_ui.py`: Lightweight initial screen with folder selection, status display, and triggers for background processing via `TaskOrchestrator`.
-   Implement `screens/loading_screen.py`: Interactive screen displaying progress, logs, phase, ETA, and controls (pause/cancel) for ongoing tasks managed by `TaskOrchestrator`.
-   Implement `screens/advanced_ui.py`: Tabbed interface for core features (Text/Image Search, AI Guessing Game, Latent Space Explorer, Duplicate Detection), ensuring all operations use `TaskOrchestrator`.
-   Fix BLIP model integration: Define `BLIP_MODEL_NAME` and ensure the captioning pipeline in `models/blip_model.py` (or equivalent) functions correctly.
-   Optimize startup:
    -   Refactor `app.py` (or main entry point) to use patterns from `app_optimized.py` and `core/fast_startup_manager.py` for instant UI rendering.
    -   Utilize `components/performance_optimizer.py` to `lazy_import` heavy modules (e.g., ML libraries like `torch`, `transformers`, `clip`) and `preload_critical_modules` only.
    -   Investigate and implement skeleton screens or placeholders during initial data/model loading phases.
-   Ensure all new UI components and background tasks are integrated with `components/task_orchestrator.py`.
-   Update documentation related to new screens, BLIP fix, and performance optimizations.

## Key Deliverables (Story Points)

| Deliverable                                                                 | Points |
| --------------------------------------------------------------------------- | :----: |
| `screens/fast_ui.py` implementation & integration with TaskOrchestrator     |   3    |
| `screens/loading_screen.py` implementation & integration with TaskOrchestrator |   5    |
| `screens/advanced_ui.py` structure and tab integration (initial)            |   3    |
| Integrate Text/Image Search tab into ADVANCED_UI using TaskOrchestrator     |   2    |
| Integrate AI Guessing Game tab into ADVANCED_UI using TaskOrchestrator    |   2    |
| Integrate Latent Space Explorer tab into ADVANCED_UI using TaskOrchestrator |   2    |
| Integrate Duplicate Detection tab into ADVANCED_UI using TaskOrchestrator   |   2    |
| Fix `BLIP_MODEL_NAME` undefined error and validate captioning pipeline      |   3    |
| Refactor `app.py` for instant UI and background loading                     |   5    |
| Implement lazy loading for heavy ML modules using `PerformanceOptimizer`    |   4    |
| Implement skeleton screens/placeholders for initial load                    |   2    |
| End-to-end integration tests for UX flow (FAST_UI -> LOADING -> ADVANCED_UI)|   3    |
| Performance benchmarking (startup time, UI responsiveness) post-optimization |   2    |
| Documentation updates for Sprint 05 deliverables                            |   2    |

_Total: 40 SP_

## Sprint Backlog

1.  **Implement FAST_UI Screen** (`screens/fast_ui.py`)
    *   UI: Folder picker, basic system status (CPU, memory if easily available), "Start Processing" button.
    *   Logic:
        *   On folder selection, validate path.
        *   On "Start Processing", submit database build/load task to `TaskOrchestrator`.
        *   Transition to LOADING screen.
    *   Performance: Ensure this screen loads < 1s.

2.  **Implement LOADING Screen** (`screens/loading_screen.py`)
    *   UI: Progress bar, dynamic text for current phase (e.g., "Loading CLIP model", "Generating embeddings"), ETA, log viewer (stream TaskOrchestrator logs), Pause/Cancel buttons.
    *   Logic:
        *   Subscribe to `TaskOrchestrator` progress updates for the active task.
        *   Implement Pause/Cancel functionality by interacting with `TaskOrchestrator` (requires orchestrator to support this).
        *   Transition to ADVANCED_UI on task completion.
        *   Handle task failure gracefully, potentially returning to FAST_UI with an error.

3.  **Implement ADVANCED_UI Screen** (`screens/advanced_ui.py`)
    *   UI: Main container with `st.tabs` for "Text Search", "Image Search", "AI Game", "Latent Explorer", "Duplicates".
    *   Logic: Each tab will encapsulate its respective feature. Ensure feature initialization and operations are offloaded to `TaskOrchestrator` where appropriate (e.g., running a new search, computing latent space).
        *   **Text/Image Search Tab**: Integrate existing search functionalities.
        *   **AI Guessing Game Tab**: Placeholder for game logic.
        *   **Latent Space Explorer Tab**: Integrate existing visualization.
        *   **Duplicate Detection Tab**: Integrate existing duplicate detection.

4.  **Fix BLIP Model Captioning**
    *   Identify where `BLIP_MODEL_NAME` should be defined (e.g., `config.py`, environment variable).
    *   Update `models/blip_model.py` or relevant captioning logic to correctly load and use the BLIP model.
    *   Add a unit test for the captioning function.
    *   Verify database build pipeline completes and captions are generated and stored.

5.  **Startup Performance Optimization**
    *   **App Refactor (`app.py`)**:
        *   Adapt `app.py` to follow the structure of `app_optimized.py` / `core/fast_startup_manager.py`.
        *   Render FAST_UI immediately.
        *   Defer all non-critical initializations.
    *   **Lazy Loading**:
        *   Identify all heavy imports (e.g., `torch`, `transformers`, `sentence_transformers`, `PIL` (if large), `numpy` (if used heavily at start), `pandas` (if used heavily at start), `sklearn`).
        *   Use `PerformanceOptimizer.lazy_import(module_name)` for these.
        *   Consider if `PerformanceOptimizer.preload_critical_modules()` can be used for genuinely critical but lightweight modules needed for FAST_UI.
    *   **Skeleton Screens**:
        *   In ADVANCED_UI tabs, display placeholders or simplified loading indicators while actual content/data is being fetched or computed by `TaskOrchestrator`.

6.  **Testing & Benchmarking**
    *   Write Playwright or Streamlit E2E tests for the FAST_UI -> LOADING -> ADVANCED_UI flow.
    *   Measure startup time (time to FAST_UI render) before and after optimizations using `scripts/performance_test.py` or similar. Target ≥50% reduction.
    *   Manually verify UI responsiveness of LOADING and ADVANCED_UI screens.

7.  **Documentation**
    *   Update `README.md` or create new documents in `/docs` for the new UI screens.
    *   Document the BLIP model fix and any configuration changes.
    *   Add a section to `THREADING_PERFORMANCE_GUIDELINES.md` (if it exists, or create it) on startup optimization patterns.
    *   Finalize this sprint doc.

## Low-Hanging Fruit for Performance (Codebase Insights)

*   **`PerformanceOptimizer.optimize_streamlit_config()`**: Ensure this is called early if it sets beneficial global Streamlit settings.
*   **`PerformanceOptimizer.optimize_memory_usage()`**: Consider calling this periodically or after heavy operations if memory fragmentation is an issue, though `gc.collect()` can be heavy.
*   **Model Caching in `LazyModelManager`**: The existing `LazyModelManager` has logic for `KEEP_MODELS_LOADED`. Ensure this is `False` during initial startup and an `OptimizedModelManager` (like in `core/optimized_model_manager.py`) is used for background loading and smarter caching.
*   **Review `utils/lazy_session_state.py`**: Ensure session state initialization is minimal and truly lazy, deferring any model or heavy data instantiation.

## Timeline & Ownership (Assumed 2-week sprint, adjust as needed)

*   **Week 1, Days 1-3:**
    *   FAST_UI implementation (Owner: Frontend) - 3 SP
    *   LOADING screen core (UI, basic progress) (Owner: Frontend) - 3 SP
    *   `app.py` refactor for instant UI (Owner: Backend/Lead) - 3 SP
*   **Week 1, Days 4-5:**
    *   LOADING screen advanced (controls, logs, ETA) (Owner: Frontend) - 2 SP
    *   Lazy loading initial implementation (Owner: Backend) - 2 SP
    *   BLIP fix investigation and implementation (Owner: Backend) - 2 SP
*   **Week 2, Days 1-3:**
    *   ADVANCED_UI structure and tab integration (Owner: Frontend) - 3 SP
    *   Integrate 2 ADVANCED_UI tabs (Owner: Full Stack) - 4 SP
    *   Refine lazy loading & `PerformanceOptimizer` integration (Owner: Backend) - 2 SP
*   **Week 2, Days 4-5:**
    *   Integrate remaining 2 ADVANCED_UI tabs (Owner: Full Stack) - 4 SP
    *   Skeleton screens implementation (Owner: Frontend) - 2 SP
    *   Testing, benchmarking, documentation (Owner: Full Team) - 8 SP

---

This plan aims to deliver a significantly improved user experience by tackling UI flow and critical performance bottlenecks.
Let's target a smooth, fast, and responsive application! 