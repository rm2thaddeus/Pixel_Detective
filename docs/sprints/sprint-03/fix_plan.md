# Sprint 03 - Fix Plan (Post-Refactor Issues)

## Date: May 26, 2025

## 1. Overview

Following a recent refactor, the application has exhibited critical issues related to database connectivity (Qdrant), data indexing, search functionality, and overall performance/responsiveness. This plan outlines the identified problems and the proposed solutions to restore and improve application stability and user experience.

## 2. Key Issues Identified

1.  **Qdrant Connection & Initialization Timing:**
    *   **Symptom:** Initial errors indicating Qdrant was unavailable, followed by successful connection later. Search failures and `NoneType` errors occurred before Qdrant was confirmed ready.
    *   **Root Cause:** Application components attempting to use Qdrant before its client (`st.session_state.qdrant_db`) was fully initialized and the collection verified.
    *   **Status:** Partially addressed by improving error handling in `QdrantDB` constructor. Docker dependency identified and Qdrant container now running.

2.  **Missing Qdrant Data Population:**
    *   **Symptom:** Searches via Qdrant return 0 results even when Qdrant is connected and the collection exists.
    *   **Root Cause:** The `DatabaseManager.build_database()` method was generating embeddings and metadata but **not** subsequently adding this data to the Qdrant collection.
    *   **Status:** `build_database` was updated to include a call to `qdrant_db.add_images_batch()`. Further testing is needed to confirm this fully resolves empty search results.

3.  **Logging `UnicodeEncodeError` on Windows:**
    *   **Symptom:** Console spammed with `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'` when logger attempts to write messages containing special characters (e.g., "→").
    *   **Root Cause:** Default Windows console encoding (often `cp1252`) cannot handle certain Unicode characters used in log messages. This occurs during model swapping logs within threaded image processing.
    *   **Impact:** Potential disruption of thread execution, performance degradation, and makes logs difficult to read.

4.  **Extreme Performance Bottleneck During Database Building:**
    *   **Symptom:** Application becomes highly unresponsive or very slow during the "build database" phase. Logged BLIP model loading times are excessively long (50-115 seconds *per image* for captioning).
    *   **Root Cause:** The `LazyModelManager._cleanup_for_model_swap()` and subsequent model loading (`get_blip_model_for_caption`, `get_clip_model_for_search`) logic appears to be repeatedly and inefficiently loading/unloading entire large models (CLIP, BLIP) for each individual image processed in `DatabaseManager.process_one` during caption generation and embedding.
    *   **Impact:** Makes database building practically unusable for any significant number of images and severely degrades UX.

5.  **Downstream `NoneType` Errors:**
    *   **Symptom:** Errors like `unsupported operand type(s) for *: 'NoneType' and 'float'` and `'NoneType' object has no attribute 'copy'`.
    *   **Root Cause:** These are consequences of earlier failures, primarily Qdrant not being ready or not containing data, leading to `st.session_state.embeddings` or other crucial variables being `None`.
    *   **Status:** Should be mitigated if Qdrant connection, data population, and the `build_database` process are fixed.

## 3. Proposed Fixes & Implementation Strategy

### 3.1. Stabilize Logging (Immediate Priority)

*   **Action:** Modify the logger configuration to handle Unicode characters gracefully on Windows or enforce UTF-8 encoding for log outputs.
    *   **Option A (Preferred):** Configure the Streamlit/Python logger (e.g., in `utils/logger.py` or main `app.py`) to use UTF-8 encoding for its handlers, especially the console handler.
    *   ```python
        # Example for basicConfig (if used)
        # logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler('app.log', 'w', 'utf-8'), logging.StreamHandler(sys.stdout)])
        # For specific handlers:
        # console_handler = logging.StreamHandler(sys.stdout)
        # console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S"))
        # console_handler.encoding = 'utf-8' # Attempt to set encoding
        # logger.addHandler(console_handler)
        ```
    *   **Option B:** Review log messages that include special characters (like "→") and replace them with ASCII alternatives (e.g., "->") if full Unicode support in the console is too problematic. This is less ideal but a quick workaround.
*   **File(s) to Edit:** `utils/logger.py` (if custom logger setup) or `app.py` (if basicConfig is used there).
*   **Verification:** Re-run database build; `UnicodeEncodeError` should be gone.

### 3.2. Optimize Model Loading and Swapping (Critical for Performance)

*   **Action:** Refactor `LazyModelManager` and its usage in `DatabaseManager.process_one` to avoid repeated full model reloads for batch operations.
    *   **Strategy 1 (Batch Processing by Model Type):**
        1.  In `DatabaseManager.build_database`, first process **all** images to get CLIP embeddings. Keep CLIP loaded.
        2.  Then, process **all** images (or those that need captions) to get BLIP captions. Load BLIP once, generate all captions, then unload.
    *   **Strategy 2 (Smarter Lazy Loading within `process_one`):**
        1.  Modify `LazyModelManager` so that `get_clip_model_for_search()` and `get_blip_model_for_caption()` only perform a swap if the *other* model is currently loaded. If the correct model is already loaded, they should just return it.
        2.  The `_cleanup_for_model_swap` should only unload a model if a *different* model is being requested.
    *   **Current `process_one` calls:**
        *   `embedding = self.model_manager.process_image(image_path)` (uses CLIP)
        *   `caption = self.model_manager.generate_caption(image_path)` (uses BLIP)
        *   This inherently causes a swap for *every image* if not managed carefully at a higher level or within `LazyModelManager`.
*   **File(s) to Edit:** `models/lazy_model_manager.py`, `database/db_manager.py` (specifically `build_database` and `process_one`).
*   **Verification:** Database build times should decrease dramatically. Log messages should show CLIP loading once for all embeddings, then BLIP loading once for all captions (or more intelligent, less frequent swaps).

### 3.3. Ensure Robust Qdrant Initialization and Data Integrity

*   **Action 1 (Qdrant Readiness Flag):**
    *   In sidebar logic (e.g., `components/sidebar/context_sidebar.py` or `ui/sidebar.py`) where `st.session_state.qdrant_db = QdrantDB(...)` is called, also set a flag: `st.session_state.qdrant_ready = True` upon successful QdrantDB instantiation *and* collection verification/creation.
    *   Modify UI components or functions that trigger search (`DatabaseManager.search_similar_images`, search UI elements) to check `st.session_state.get('qdrant_ready', False)` before proceeding. If not ready, display an appropriate "initializing" message.
*   **Action 2 (Verify `load_database` for Qdrant):**
    *   If Qdrant is intended to be the primary database, the `DatabaseManager.load_database()` method should also populate Qdrant from the loaded `.npy`/`.csv` files if Qdrant is empty but local files exist. This ensures consistency if the app is restarted. (Currently, it only loads into session state for in-memory fallback).
    *   Alternatively, always prioritize building/loading into Qdrant, and treat local files purely as a cache or a source for the initial Qdrant build.
*   **File(s) to Edit:** `components/sidebar/context_sidebar.py`, `ui/sidebar.py`, `database/db_manager.py`.
*   **Verification:** No "Qdrant not available" messages if Qdrant is running. Searches should consistently use Qdrant if it's ready and populated. `NoneType` errors related to missing embeddings/data should disappear.

### 3.4. Address TensorFlow/Keras Deprecation Warning

*   **Action:** Change `tf.reset_default_graph` to `tf.compat.v1.reset_default_graph`.
*   **File(s) to Edit:** This warning originates from an installed Keras package file (`keras/src/backend/common/global_state.py`). Directly editing installed packages is generally not recommended.
    *   **Best approach:** Consider upgrading TensorFlow/Keras to versions where this is resolved.
    *   **Alternative (if upgrade not feasible):** Suppress the specific warning if it's too noisy, but this is a workaround, not a fix.
*   **Verification:** Deprecation warning should no longer appear in logs.

## 4. Order of Implementation

1.  **Stabilize Logging** (to make debugging easier and prevent related disruptions).
2.  **Optimize Model Loading and Swapping** (this is the biggest performance killer).
3.  **Ensure Robust Qdrant Initialization and Data Integrity** (to ensure reliable search).
4.  **Address TensorFlow/Keras Deprecation Warning** (lower priority).

## 5. Expected Outcome

*   Application is responsive during database building and normal operation.
*   Searches correctly use Qdrant and return relevant results.
*   Logs are clean of `UnicodeEncodeError` and `NoneType` errors related to database/search.
*   Overall application stability and UX are significantly improved. 