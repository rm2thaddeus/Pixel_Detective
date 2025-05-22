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
  - `main_interface.py`, `sidebar.py`, `tabs.py`: Streamlit UI components.
- **utils/**
  - `image_utils.py`: Image loading, resizing, preprocessing.
  - `logger.py**: Standardized logging.
  - `cuda_utils.py`: CUDA checks and memory usage logging.
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
│   └── cuda_utils.py
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

## 2. Content‑Addressable Caching

**Goal:**  
Prevent redundant embedding computations by caching embeddings based on file content hash.

**Tasks:**
- [x] Integrate a lightweight cache (SQLite, Redis, or JSON) for hash→embedding mapping.
- [x] Check cache before embedding; reuse if present, otherwise compute and store.
- [x] Integrate into both CLI and Streamlit pipelines.

---

## 3. Background Job Offloading

**Goal:**  
Keep the Streamlit UI responsive by offloading heavy tasks to background workers.

**Tasks:**
- [x] Integrate Celery with Redis (or use Python's `concurrent.futures` for local jobs).
- [x] Wrap ingestion and embedding as asynchronous tasks.
- [x] Update Streamlit UI to trigger and monitor background jobs, with progress bars and completion notifications.

---

## 4. Incremental Indexer

**Goal:**  
Automatically index new or changed files in Qdrant without full reprocessing.

**Tasks:**
- [ ] Add a file-system watcher (e.g., `watchdog`) to monitor target folders.
- [ ] On file creation/modification, compute embeddings (with cache) and upsert to Qdrant.
- [ ] Handle deletions by removing from Qdrant.

---

## 5. Latent Space Visualization

**Goal:**  
Enable interactive exploration of embedding space for debugging and discovery.

**Tasks:**
- [ ] After batch embedding, fit UMAP/t-SNE (scikit-learn).
- [ ] Generate a DataFrame with 2D coordinates and labels.
- [ ] Display interactive scatterplot in Streamlit (Plotly or built-in chart).
- [ ] Allow click-through to open associated images.

---

## 6. Duplicate Detection (Post-Embedding)

**Goal:**  
Identify and manage near-duplicate images using vector similarity.

**Tasks:**
- [ ] Compute cosine similarity within Qdrant to find duplicates.
- [ ] Add "Find duplicates" action in UI.
- [ ] Present results with side-by-side previews and options to tag, merge, or delete.

---

## 7. Metadata-Based Filtering

**Goal:**  
Enable fine-grained search and filtering using EXIF metadata.

**Tasks:**
- [ ] Extract and store EXIF metadata alongside embeddings in Qdrant.
- [ ] Extend Streamlit sidebar with filters (date, lens, location, etc.).
- [ ] Update query logic to combine vector similarity with metadata constraints.

---

## Timeline & Priorities

| Feature                     | Estimated Effort | Priority |
|-----------------------------|------------------|----------|
| Early Duplicate Detection   | 1–2 days         | Highest  |
| Content‑Addressable Caching | 1–2 days         | High     |
| Background Job Offloading   | 2–3 days         | High     |
| Incremental Indexer         | 1–2 days         | Medium   |
| Latent Space Visualization  | 1–2 days         | Medium   |
| Duplicate Detection (Post)  | 2 days           | Medium   |
| Metadata-Based Filtering    | 1–2 days         | Low      |

---

**Note:**  
Implement features in order of priority for maximum impact and efficiency.  
This list will be updated as features are completed or new needs arise. 

---

**Update (2024-06-12):**
- Content-addressable embedding cache and background job offloading are now fully integrated in both CLI and Streamlit pipelines. The Streamlit UI shows live progress, and all embedding computations are cache-aware for efficiency.