# Threading & Performance Guidelines for Pixel Detective

## 0. Task Orchestrator Integration

- Route all background tasks through the `TaskOrchestrator` in `components/task_orchestrator.py`, avoiding direct `threading.Thread` instantiation.
- Use the orchestrator's API (`submit(name, fn, *args) -> bool`, `is_running(name) -> bool`) to enforce single-thread per job and manage task lifecycle.

This guide consolidates best practices to maintain clear background threading, avoid redundant heavy imports, and ensure thread safety in our Streamlit-based image search app.

## 1. Heavy Modules Import
- Centralize all heavy ML/Data library imports (e.g., `torch`, `transformers`, `PIL`, `pandas`) into a single background operation.
- **Cache imports** with `@st.cache_resource` where possible to enforce one-time loading across reruns.
- **Guard thread spawn** using a `heavy_import_started` flag in `LoadingProgress` to prevent duplicate import threads.

## 2. BackgroundLoader Pipeline
- Use a single instance of `BackgroundLoader` to manage the full processing pipeline (preparation, scanning, database build).
- **Preserve import state** across pipeline resets: carry over `heavy_modules_imported` and `heavy_import_started` flags when resetting `LoadingProgress`.
- **Inline preparation** (in pipeline) should only run if no import is in progress or already completed.

## 3. Thread Safety and Session State
- **Do NOT access** `st.session_state` from background threads. All background work should communicate via the thread-safe `LoadingProgress` object.
- **UI components** must check for readiness flags (e.g., `database_ready`, `models_loaded`) before calling session-based managers.

## 4. Caching of Managers
- Decorate model and database manager factories with `@st.cache_resource(show_spinner=False)` to ensure a single shared instance:
  - `get_cached_model_manager`
  - `get_cached_db_manager`

## 5. Component Development
- In any UI component or screen:
  1. Check `st.session_state.get('database_ready', False)` before invoking database operations.
  2. Wrap session access in thread-safe guards:
     ```python
     if not st.session_state.get('database_ready', False):
         st.info("Database not ready—please wait.")
         return
     ```
  3. Avoid direct background thread launches in component code; delegate to `BackgroundLoader`.

## 6. Adding Future Background Tasks
1. **Define state flags** in `LoadingProgress` for new task phases (e.g., `feature_extraction_started`).
2. **Guard thread creation** with those flags in `start_background_preparation` or a similar entry.
3. **Update progress** under `self._lock` to ensure consistent UI updates.
4. **Signal completion** via progress object, trigger UI rerun only when safe.

## 7. Avoiding Common Pitfalls
- Multiple calls to `start_background_preparation` can spawn parallel threads; always guard with flags.
- Inline calls to `prepare_heavy_modules` in the loading pipeline must respect in-progress state.
- Never rely on `heavy_modules_imported` alone to prevent re-import; use a distinct `heavy_import_started` flag.

---

Following these guidelines will help keep our codebase organized, performant, and safe for future enhancements. Use this doc as the single source of truth for threading and performance patterns in Pixel Detective. 