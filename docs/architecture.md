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

## 3.5. Hybrid Search System

The Pixel Detective search system implements a sophisticated hybrid approach combining vector similarity with metadata filtering:

### A. Query Processing (`utils/query_parser.py`)
1. **Query Parsing**: Analyzes user input to extract:
   - Metadata constraints (e.g., `camera:canon`, `iso:100`)
   - Semantic query text for vector search
   - Field aliases (e.g., `aperture_value` → `aperture`)
2. **Normalization**: Converts all fields and values to lowercase for consistent matching
3. **Filter Building**: Creates Qdrant-compatible filters using SHOULD (OR) logic instead of restrictive MUST (AND) logic

### B. Search Execution (`database/db_manager.py`, `database/qdrant_connector.py`)
1. **Vector Encoding**: Text queries are encoded using CLIP for semantic similarity
2. **Hybrid Search**: Uses Qdrant's Query API with RRF (Reciprocal Rank Fusion):
   - Primary vector search for semantic relevance
   - Metadata boosting for exact matches
   - Soft constraint filtering that enhances rather than restricts results
3. **Result Fusion**: Combines vector similarity scores with metadata match scores

### C. Metadata Field Mapping
- **Comprehensive Coverage**: Supports 80+ metadata fields from EXIF/XMP extraction
- **Field Aliases**: Maps extracted field names to user-friendly query terms
- **Automatic Enrichment**: Extracts year from date fields, normalizes camera makes/models
- **Case-Insensitive Matching**: All string comparisons use case-insensitive logic

### D. Search Logic Principles
- **Always Return Results**: Users always see relevant images, even with non-matching filters
- **Boost, Don't Block**: Metadata filters boost relevance rather than create hard restrictions
- **Flexible Queries**: Natural language works alongside technical specifications
- **Progressive Enhancement**: Vector search provides baseline results, metadata refines ranking

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

---

# Next Sprint: UI Improvements & Performance Optimization

With the core hybrid search system now implemented, the next development sprint focuses on enhancing user experience and optimizing application performance before merging to main branch.

## 🎯 Architecture Focus Areas

### **1. Streamlit Application Performance**

**Current State:**
- ✅ Model persistence in session state
- ✅ CUDA memory management 
- ✅ Custom CSS and UI components
- ❌ Potential rendering bottlenecks
- ❌ Suboptimal model loading strategy
- ❌ Database operations not optimized

**Target Improvements:**
- **Lazy Loading Strategy**: Implement on-demand component and model loading
- **Rendering Optimization**: Cache heavy UI components, eliminate redundant re-renders
- **Memory Management**: Smart cleanup of session state, optimized CUDA usage
- **Database Performance**: Query caching, connection optimization

### **2. CLI Application Feature Parity**

**Current State:**
- ✅ Basic batch processing (CLIP + BLIP)
- ✅ Qdrant database integration
- ✅ Embedding cache and duplicate detection
- ❌ Missing hybrid search capabilities
- ❌ No metadata-based filtering
- ❌ Limited query functionality

**Target Improvements:**
- **Hybrid Search Integration**: Port query parser and RRF fusion to CLI
- **Interactive Search Mode**: Real-time query processing
- **Advanced Filtering**: Metadata-based search with CLI flags
- **Result Export**: Multiple output formats for search results

### **3. Unified Model Management**

**Current Architecture Gap:**
- Different model loading strategies between app.py and mvp_app.py
- Inconsistent memory management patterns
- No shared configuration for optimization settings

**Target Architecture:**
- **Shared ModelManager**: Common model management across CLI and UI
- **Configuration Unification**: Centralized performance settings
- **Memory Optimization**: Consistent CUDA management patterns

### **4. Performance Monitoring & Optimization**

**Missing Infrastructure:**
- No performance metrics collection
- Limited profiling capabilities
- No automated benchmarking

**Target Implementation:**
- **Metrics Collection**: Startup time, search response, memory usage
- **Profiling Tools**: Integration with Streamlit profiler, memory tracking
- **Benchmarking Suite**: Automated performance regression testing

---

## 🔄 Integration Strategy

### **Phase 1: Core Performance (Week 1)**
1. **Streamlit Optimization**: Lazy loading, caching, rendering improvements
2. **Model Management**: Smart loading/unloading strategies
3. **Memory Optimization**: Session cleanup, CUDA efficiency

### **Phase 2: Feature Parity (Week 1-2)**
1. **CLI Enhancement**: Add hybrid search and metadata filtering
2. **Unified Codebase**: Shared components between CLI and UI
3. **Configuration Management**: Centralized settings

### **Phase 3: Polish & Monitoring (Week 2)**
1. **Performance Monitoring**: Metrics, profiling, benchmarking
2. **User Experience**: Loading states, error handling, responsiveness
3. **Documentation**: Performance guides, optimization tips

---

## 📊 Success Metrics

### **Performance Targets:**
- **Startup Time**: < 10 seconds for model loading
- **Search Response**: < 2 seconds for typical queries
- **Memory Usage**: Stable session state, no memory leaks
- **UI Responsiveness**: No blocking operations > 1 second

### **Feature Completeness:**
- **CLI Parity**: Full hybrid search support in mvp_app.py
- **Code Reuse**: Shared components between CLI and UI
- **User Experience**: Consistent behavior across interfaces

---

**Note:** This sprint prepares the application for production deployment and main branch merge. All optimizations will be documented and benchmarked to ensure measurable improvements.