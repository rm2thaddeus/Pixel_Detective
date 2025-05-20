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

### Changed
- Upgraded to CUDA-enabled PyTorch (torch==2.7.0+cu118, torchvision==0.22.0+cu118, torchaudio==2.7.0+cu118) for GPU acceleration.
- Updated `docs/README.md` with new installation, verification, and troubleshooting instructions for CUDA-enabled PyTorch.
- Merged `docs/current_requirements.txt` into `requirements.txt` and deleted the former.
- Updated `docs/architecture.md` and `docs/roadmap.md` to reference the new environment setup and GPU troubleshooting.
- Refactored `scripts/mvp_app.py` to:
    - Use `database.qdrant_connector.QdrantDB` for all database operations.
    - Utilize the new `add_images_batch` method for improved performance.
    - Use a distinct Qdrant collection name `pixel_detective_mvp`.

### Fixed
- Resolved disk space issues by purging pip cache (`pip cache purge`).
- Ensured all scripts and the MVP pipeline now use the GPU if available.

### Removed
- Deleted `scripts/pipeline.py` as its core functionalities (CLIP processing, image understanding) are now integrated into `models/clip_model.py` and `scripts/mvp_app.py`.
- Deleted `scripts/embedding.py` as its DNG/RAW handling and embedding logic are now part of `models/clip_model.py`.
- Deleted the old root `vector_db.py` (replaced by `database/qdrant_connector.py` and `database/db_manager.py` for the Streamlit app).

### Notes
- If you see `torch.cuda.is_available() == False`, check your NVIDIA drivers, CUDA toolkit, and ensure you installed the correct PyTorch version for your CUDA version.
- If you run out of disk space during installation, clear your pip cache with `pip cache purge`. 