# CHANGELOG

## [Unreleased]

### Added
- Created this changelog to track environment and documentation changes.
- Full support for DNG (RAW) images: DNG files are now processed for both CLIP embeddings and BLIP captions using rawpy and PIL interoperability.
- Results summary: After each batch run, a summary of all processed images, their captions, and embedding status can be printed and saved to results_summary.txt in the project root by using the --save-summary flag (default: off).
- Enhanced `database/qdrant_connector.py` (QdrantDB class) with:
    - Batch insertion (`add_images_batch`).
    - More robust error handling and logging.
    - Additional configuration options for Qdrant client (GRPC, API key, timeout).
    - Helper for vector preparation and validation.
    - Methods to get collection info and delete collection.
- Enhanced `models/clip_model.py` with:
    - Integrated DNG/RAW file handling directly in `process_image`.
    - Completed `process_batch` function for efficient batch embedding generation.
- Early duplicate detection: Added `scripts/find_duplicates.py` CLI tool and `utils/duplicate_detector.py` for pre-pipeline duplicate and near-duplicate detection using SHA-256 and perceptual hashing (phash), with EXIF extraction and CSV/console reporting.
- Content-addressable embedding cache: Added `utils/embedding_cache.py` (SQLite-based) and integrated cache checks into CLI MVP (`scripts/mvp_app.py`) to prevent redundant embedding computation.
- Background job offloading: Integrated `concurrent.futures` for parallel BLIP captioning in CLI MVP and Streamlit pipelines, improving responsiveness and throughput.

### Changed
- Upgraded to CUDA-enabled PyTorch (torch==2.7.0+cu118, torchvision==0.22.0+cu118, torchaudio==2.7.0+cu118) for GPU acceleration.
- Updated `docs/README.md` with new installation, verification, and troubleshooting instructions for CUDA-enabled PyTorch.
- Merged `docs/current_requirements.txt` into `requirements.txt` and deleted the former.
- Updated `docs/architecture.md` and `docs/roadmap.md` to reference the new environment setup and GPU troubleshooting.
- Refactored `scripts/mvp_app.py` to:
    - Use `database.qdrant_connector.QdrantDB` for all database operations.
    - Utilize the new `add_images_batch` method for improved performance.
    - Use a distinct Qdrant collection name `pixel_detective_mvp`.
    - Integrate embedding cache and duplicate detection logic.
    - Use parallel background jobs for BLIP captioning.
- Streamlit app (`app.py`): Improved model management, error handling, and background job offloading for a more responsive UI. Embedding cache is now checked before computation.
- Streamlit app: Added Latent Space Explorer tab with UMAP+Plotly visualization and sidebar controls for metadata coloring and UMAP hyperparameters.
- Latent Space Explorer: Replaced the lasso/selection-enabled Plotly scatter plot with a robust, minimal scatter plot using plotly.graph_objects. This resolves issues with invisible points and color/selection conflicts. Extensive UI debugging was required due to Plotly/Streamlit quirks, including:
    - Points not rendering despite valid data (caused by color/selection property conflicts and over-customization).
    - The need to use only one color assignment method (either in px.scatter or update_traces, not both).
    - Removal of all lasso/selection logic for maximum reliability.
    - Final solution uses a single, explicit go.Scatter plot for clarity and robustness.

### Fixed
- Resolved disk space issues by purging pip cache (`pip cache purge`).
- Ensured all scripts and the MVP pipeline now use the GPU if available.
- Fixed thread-safety in `utils/embedding_cache.py` by setting `check_same_thread=False` and guarding DB access with a lock to support concurrent embeddings.
- Replaced background-thread progress updates in the Streamlit UI with `st.spinner` spinners to avoid `NoSessionContext` errors during database builds and merges.
- Enhanced `DatabaseManager.load_database` to catch empty or invalid metadata CSVs, delete corrupted database files, and force a rebuild on the next run.
- Removed redundant radio-mode selector; simplified tab navigation in Streamlit UI.

### Removed
- Deleted `scripts/pipeline.py` as its core functionalities (CLIP processing, image understanding) are now integrated into `models/clip_model.py` and `scripts/mvp_app.py`.
- Deleted `scripts/embedding.py` as its DNG/RAW handling and embedding logic are now part of `models/clip_model.py`.
- Deleted the old root `vector_db.py` (replaced by `database/qdrant_connector.py` and `database/db_manager.py` for the Streamlit app).

### Notes
- If you see `torch.cuda.is_available() == False`, check your NVIDIA drivers, CUDA toolkit, and ensure you installed the correct PyTorch version for your CUDA version.
- If you run out of disk space during installation, clear your pip cache with `pip cache purge`.
- Implementing this feature was unexpectedly challenging due to subtle Plotly/Streamlit UI interactions. Developers should be aware that even with valid data, UI rendering can silently fail if marker/color/selection properties are misused. Always start with a minimal plot and add features incrementally. 