# CHANGELOG

## [Unreleased]

### Planned - Next Sprint: UI Improvements & Performance Optimization
- **Streamlit Performance Optimization**: Lazy loading, component caching, memory management
- **CLI Feature Parity**: Port hybrid search and metadata filtering to mvp_app.py  
- **Unified Architecture**: Shared ModelManager and database components between CLI and UI
- **Performance Monitoring**: Metrics collection, benchmarking suite, profiling tools
- **User Experience Polish**: Loading states, error handling, visual optimizations
- **Latent Space Explorer Overhaul**: Complete redesign of visualization tab
  - **Plotly Implementation Issues**: Current scatter plot has rendering problems and poor interactivity
  - **Performance Problems**: Slow rendering with large datasets, memory inefficiency
  - **Missing Features**: No proper selection tools, limited metadata integration, poor clustering visualization
  - **Target Improvements**: Fast, responsive scatter plots with proper selection, better clustering, metadata overlays
  - **Alternative Solutions**: Consider switching to more performant visualization libraries (Bokeh, Altair)

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
- **Hybrid Search Implementation**: Complete rewrite of search functionality using Qdrant's Query API
  - **Core Architecture**: Implemented proper RRF (Reciprocal Rank Fusion) for combining vector and metadata search results
  - **Comprehensive Metadata Support**: Extract and index 80+ metadata fields from EXIF/XMP data:
    - Camera settings (aperture, ISO, focal length, shutter speed, exposure program, white balance, flash settings)
    - Geographic information (GPS coordinates, location names, city, country)
    - Temporal data (dates taken, modified, digitized with automatic year extraction)
    - Technical details (color temperature, contrast, saturation, lens info, camera serial numbers)
    - Content classification (tags, keywords, subject, caption integration)
  - **Advanced Query Parser** (`utils/query_parser.py`):
    - Generic key:value parsing for any metadata field (e.g., `camera:canon`, `iso:100`, `aperture:2.8`)
    - Field aliases mapping for user-friendly queries (`aperture_value` → `aperture`, `Keywords` → `keywords`)
    - Case-insensitive matching for all string comparisons with automatic normalization
    - Smart text extraction that separates semantic queries from metadata constraints
  - **Intelligent Search Logic**: 
    - SHOULD-based filter logic instead of restrictive MUST constraints for better recall
    - Soft constraint filtering that boosts relevance rather than blocking results
    - Progressive enhancement where vector search provides baseline, metadata refines ranking
    - Users always see results even when metadata filters don't perfectly match
  - **Data Migration & Population**:
    - Created `scripts/upload_to_qdrant.py` for migrating existing embeddings and metadata to Qdrant
    - Supports batch uploading with data validation, cleaning, and integrity checks
    - Maintains data consistency between embeddings and metadata records
  - **Query Examples Supported**:
    - Natural language: `"happy family photos"`, `"sunset landscape"`
    - Technical specs: `"iso:100 aperture:2.8"`, `"camera:canon lens:50mm"`
    - Combined queries: `"strasbourg 2023 family"`, `"sunset photos taken with Canon"`
    - Flexible matching: Partial matches still return relevant results

### Changed
- Upgraded to CUDA-enabled PyTorch (torch==2.7.0+cu118, torchvision==0.22.0+cu118, torchaudio==2.7.0+cu118) for GPU acceleration.
- Updated `docs/README.md` with new installation, verification, and troubleshooting instructions for CUDA-enabled PyTorch.
- Merged `docs/current_requirements.txt` into `requirements.txt` and deleted the former.
- Updated `