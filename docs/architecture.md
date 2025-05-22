# Architecture Overview

This document describes the high-level architecture of the Pixel Detective application, including core modules, data flow, and key components.

## 0. Environment Setup

- Use a Python virtual environment (`.venv`) for dependency isolation.
- Activate on Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- Activate on Unix/macOS: `source .venv/bin/activate`
- **Install CUDA-enabled PyTorch** for GPU acceleration. See the README for installation and troubleshooting instructions.
- If you see `torch.cuda.is_available() == False`, check your drivers and CUDA install, and ensure you have the correct PyTorch version for your CUDA toolkit.

## 1. Application Modes

- **Streamlit App (`app.py`)**: Interactive UI for image search, exploration, and AI games.
- **CLI MVP (`scripts/mvp_app.py`)**: Command-line tool for batch ingestion, embedding, captioning, and database creation. Optimized for large-scale, headless processing.

## 2. Core Modules & Directory Structure

- **config.py**: Global settings (e.g., GPU memory efficiency, model loading).
- **models/**
  - `clip_model.py`: CLIP model logic, including DNG/RAW support and batch processing.
  - `blip_model.py`: BLIP model logic for captioning.
  - `model_manager.py`: Loads and manages models for the Streamlit app.
- **metadata_extractor.py**: Extracts file metadata and image EXIF data.
- **database/**
  - `qdrant_connector.py`: QdrantDB class for all vector DB operations (batch upsert, search, collection management).
  - `db_manager.py`: Higher-level DB management for the Streamlit app.
  - `vector_db.py`: (Legacy, used by Streamlit app; new code uses `qdrant_connector.py`.)
- **ui/**
  - `main_interface.py`, `sidebar.py`, `tabs.py`: Streamlit UI components for search and games.
  - `latent_space.py`: Latent Space Explorer tab for embedding visualization (UMAP & Plotly scatter) with cached projections, dynamic sampling, and interactive click/lasso selection.
- **utils/**
  - `image_utils.py`: Image loading, resizing, preprocessing.
  - `logger.py**: Standardized logging.
  - `cuda_utils.py`: CUDA checks and memory usage logging.
  - `incremental_indexer.py`: File system watcher and incremental indexing logic.
  - `embedding_cache.py`: Cache for embedding computations.
- **scripts/**
  - `mvp_app.py`: CLI MVP for batch processing.
  - `diagnose_cuda.py`: GPU diagnostics.
  - `minigame.py`: AI guessing game prototype.
  - `run_app.bat`: Windows launcher for the Streamlit app.

## 3. Data Flow

### A. Streamlit App (`app.py`)
1. User selects or uploads an image folder via the sidebar.
2. `ModelManager` loads CLIP and BLIP models (with device selection and optional quantization).
3. `metadata_extractor.py` processes images for metadata.
4. `DatabaseManager` (using `db_manager.py` and `qdrant_connector.py`) stores embeddings and metadata in Qdrant.
5. UI components (`ui/`) display search results, comparisons, and game interactions.

### B. CLI MVP (`scripts/mvp_app.py`)
1. User runs the script with a folder path.
2. Images are processed in batches:
   - CLIP embeddings (with DNG/RAW support)
   - BLIP captions (parallelized)
   - Metadata extraction
3. Batch upsert to Qdrant via `QdrantDB`.
4. Optionally outputs a summary (`results_summary.txt`) and a detailed CSV.

### C. Latent Space Explorer (`ui/latent_space.py`)
1. Fetch embeddings and metadata via `DatabaseManager.get_latent_space_data()`.
2. Compute and cache 2D UMAP projection of embedding vectors for responsive rerenders.
3. Render a minimal, robust Plotly scatter plot (using plotly.graph_objects) for all points.
4. **DBSCAN clustering overlay:** After UMAP projection, DBSCAN is run on the 2D coordinates. Points are colored by cluster label, with outliers (noise, label -1) shown in gray. A sidebar slider allows interactive tuning of the DBSCAN `eps` (cluster radius) parameter. This enables visual exploration of clusters and outliers in the embedding space.
5. Extensive UI debugging was required: Plotly/Streamlit can silently fail to render points if marker/color/selection properties are misused. The current approach prioritizes reliability and clarity.

## 4. Batch Processing & Results

- **Batch size** is configurable for both CLIP and BLIP (CLI MVP).
- **Results summary**: CLI MVP can print and save a summary of all processed images, captions, and embedding status (`--save-summary` flag).
- **Detailed CSV**: CLI MVP can output a CSV with all metadata, captions, and embedding status.

## 5. RAW/DNG Image Support

- DNG/RAW files are handled natively in both the Streamlit app and CLI MVP.
- When a DNG file is encountered, it is loaded using `rawpy` and converted to RGB before processing by CLIP/BLIP.

## 6. Static Assets & Test Data

- **.streamlit/static/**: Contains app icons (e.g., `detective.png`).
- **Library Test/**: Contains test images and scripts for development/testing.
- **docs/**: Documentation, including this file, roadmap, and changelog.

## 7. Deployment & Scaling

- Designed for consumer GPUs (6GB VRAM minimum), but falls back to CPU.
- Batch processing and memory-efficient options for large collections.
- QdrantDB supports both local and remote (cloud) deployments.
- CLI MVP can be run headless for large-scale ingestion.

## 8. File/Directory Structure (Current)

```
project_root/
│
├── app.py
├── config.py
├── metadata_extractor.py
├── requirements.txt
│
├── models/
│   ├── clip_model.py
│   ├── blip_model.py
│   └── model_manager.py
│
├── database/
│   ├── qdrant_connector.py
│   ├── db_manager.py
│   └── vector_db.py
│
├── ui/
│   ├── main_interface.py
│   ├── sidebar.py
│   └── tabs.py
│
├── utils/
│   ├── image_utils.py
│   ├── logger.py
│   ├── cuda_utils.py
│   ├── incremental_indexer.py
│   └── embedding_cache.py
│
├── scripts/
│   ├── mvp_app.py
│   ├── diagnose_cuda.py
│   ├── minigame.py
│   └── run_app.bat
│
├── .streamlit/
│   ├── custom.css
│   ├── config.toml
│   └── static/
│       └── detective.png
│
├── Library Test/
│   └── (test images, .csv, .npy, extract_xmp.py, etc.)
│
└── docs/
    ├── architecture.md
    ├── roadmap.md
    ├── CHANGELOG.md
    └── README.md
```

## 9. Notes

- For large image collections, processing may take time; GPU acceleration is highly recommended.
- The CLI MVP is the preferred tool for initial database creation and bulk ingestion.
- The Streamlit app is ideal for interactive exploration, search, and demonstration.

# Pixel Detective – To-Do List

This document tracks planned enhancements and optimizations for the Pixel Detective project. Each item is actionable and prioritized for efficient, high-impact development.

---

## 1. Early Duplicate Detection (Pre-Pipeline)

**Goal:**  
Detect and handle duplicate images before running embedding/captioning to save compute and storage.

**Tasks:**
- [x] Implement content hash (e.g., SHA-256) computation for all files in the input folder.
- [x] Build a hash→file mapping to identify exact duplicates.
- [x] Optionally, extract key EXIF fields (DateTimeOriginal, CameraSerialNumber, etc.) for additional duplicate/near-duplicate detection.
- [x] Present duplicates to the user for review or automatically select which to keep.
- [x] (Optional) Implement perceptual hashing for near-duplicate detection (e.g., RAW+JPEG pairs).

**Implementation Note:**
A CLI script (`scripts/find_duplicates.py`) is provided to scan any folder for exact and near-duplicate images. It supports:
- SHA-256 content hashing for exact duplicates
- Perceptual hashing (phash) for near-duplicates, with configurable threshold
- Optional EXIF extraction for review
- Console and CSV reporting

---

## 2. Content-Addressable Caching

**Goal:**  
Prevent redundant embedding computations by caching embeddings based on file content hash.

**Tasks:**
- [x] Integrate a lightweight cache (SQLite, Redis, or JSON) for hash→embedding mapping.
- [x] Check cache before embedding; reuse if present, otherwise compute and store.
- [x] Integrate into both CLI and Streamlit pipelines.

**Implementation Note:**
- The SQLite-based cache (`utils/embedding_cache.py`) is configured with `check_same_thread=False` and uses a threading lock to allow safe concurrent access in both CLI and Streamlit.

---

## 3. Background Job Offloading

**Goal:**  
Keep the Streamlit UI responsive by offloading heavy tasks to background workers.

**Tasks:**
- [x] Integrate Celery with Redis (or use Python's `concurrent.futures` for local jobs).
- [x] Wrap ingestion and embedding as asynchronous tasks.
- [x] Update Streamlit UI to trigger and monitor background jobs, with progress bars and completion notifications.

**Implementation Note:**
- UI progress indicators now use Streamlit's `st.spinner` for synchronous feedback instead of manual background-thread progress updates, preserving the session context.

---

## 4. Incremental Indexer

**Goal:**  
Automatically index new or changed files in Qdrant without full reprocessing.

**Tasks:**
- [x] Add a file-system watcher (e.g., `watchdog`) to monitor target folders (implemented in `utils/incremental_indexer.py`).
- [x] On file creation/modification, compute embeddings (with cache), generate caption, and upsert to Qdrant.
- [x] Handle deletions by removing from Qdrant using `delete_image` in `database/qdrant_connector.py`.

---

## 5. Latent Space Visualization

**Goal:**  
Enable fast, beautiful, and insightful exploration of the embedding space.

**Tasks:**
- [x] Add Latent Space Explorer tab with UMAP+Plotly visualization and sidebar controls for metadata coloring and UMAP hyperparameters.
- [x] Precompute and cache UMAP projections to minimize latency on tab switch and re-renders.
- [x] Implement sampling or pagination for large datasets to prevent UI freezing.
- [x] Improve plot aesthetics: custom color scales, thumbnail-on-hover, zoom/pan, and clear legends.
- [x] Eliminate UI flashing by using `st.experimental_memo` or session-based caching of computed projections.
- [x] **Add DBSCAN clustering overlays to highlight structure in the latent space.**


---

## 6. Duplicate Detection (Post-Embedding)

**Goal:**  
Identify and manage near-duplicate images using vector similarity.

**Tasks:**
- [x] Compute cosine similarity within Qdrant to find duplicates.
- [x] Add "Find duplicates" action in UI.
- [x] Present results with side-by-side previews and options to tag, merge, or delete.

**Implementation Note:**
- The duplicate detection feature is now fully integrated in the app. Qdrant must be running (e.g., via Docker) for the database and duplicate detection to work. Once Qdrant was started, the feature worked perfectly in the UI.

---

## 7. Metadata-Based Filtering

**Goal:**  
Enable fine-grained search and filtering using EXIF metadata.

**Tasks:**
- [ ] Extract and store EXIF metadata alongside embeddings in Qdrant.
- [ ] Extend Streamlit sidebar with filters (date, lens, location, etc.).
- [ ] Update query logic to combine vector similarity with metadata constraints.

---

## 8. UI Improvements & Performance Optimization

**Goal:**
Consolidate UI fixes and enhance app responsiveness and load times.

**Tasks:**
- [ ] Audit and fix remaining UI issues across all tabs (selection tools, metadata accuracy).
- [ ] Optimize Streamlit rendering, reduce flashing and redundant computations.
- [ ] Leverage session and data caching for all heavy operations (database load, UMAP).
- [ ] Minify and lazy-load static assets (images, CSS).
- [ ] Benchmark and profile app startup and interactive interactions.

---

## Timeline & Priorities

| Feature                     | Estimated Effort | Priority |
|-----------------------------|------------------|----------|
| Early Duplicate Detection   | 1–2 days         | Highest  |
| Content-Addressable Caching | 1–2 days         | High     |
| Background Job Offloading   | 2–3 days         | High     |
| Incremental Indexer         | 1–2 days         | Medium   |
| Latent Space Visualization  | 1–2 days         | Medium   |
| Duplicate Detection (Post)  | 2 days           | Medium   |
| Metadata-Based Filtering    | 1–2 days         | Low      |
| UI Improvements & Performance Optimization | 2–3 days | Medium |

---

**Note:**  
Implement features in order of priority for maximum impact and efficiency.  
This list will be updated as features are completed or new needs arise. 

---

**Update (2024-06-12):**
- Content-addressable embedding cache and background job offloading are now fully integrated in both CLI and Streamlit pipelines. The Streamlit UI shows live progress, and all embedding computations are cache-aware for efficiency.

---

# Changelog

**2024-06-12**
- Latent Space Explorer now supports DBSCAN clustering overlays. After UMAP projection, clusters are detected and visualized with color, and outliers are shown in gray. The DBSCAN `eps` parameter is adjustable in the UI for interactive exploration. Debug output has been removed for a cleaner user experience.

**2024-06-13**
- Implemented and debugged hybrid (vector + metadata) search with Qdrant.
- Added modular query parser and robust fallback logic for user-friendly search.
- Improved debug logging for search diagnostics.