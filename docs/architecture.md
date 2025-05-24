# Architecture Overview

This document describes the high-level architecture of the Pixel Detective application, including core modules, data flow, and key components.

## 🎯 **Sprint 01 Complete**: Unified 3-Screen Architecture ✅

**Status**: Successfully transformed fragmented dual UI system into unified 3-screen architecture  
**Achievement**: UI/UX integration complete with performance maintained  
**Result**: 
- ✅ **Unified user experience** - Single coherent 3-screen flow
- ✅ **Component integration** - All sophisticated features accessible  
- ✅ **Performance preserved** - <1s startup maintained
- ✅ **User-focused design** - Removed technical jargon, added engaging progress
- ✅ **Graceful fallbacks** - Components work with error handling

**Completed Transformations**:
1. **Screen 1**: Simplified user-focused folder selection (removed technical metrics)
2. **Screen 2**: Engaging progress experience (replaced boring technical logs)  
3. **Screen 3**: Sophisticated features integrated (real components with fallbacks)
4. **Component Architecture**: Extracted `ui/` components to organized `components/` structure

## 🏗️ New Unified Architecture (Post Sprint 01)

### Screen-Based Architecture
```
screens/
├── fast_ui_screen.py     # ✅ Screen 1: Simplified & user-focused  
├── loading_screen.py     # ✅ Screen 2: Engaging progress experience
└── advanced_ui_screen.py # ✅ Screen 3: Sophisticated with real components
```

### Component System (NEW)
```
components/
├── search/               # Text search, image search, AI games, duplicates
│   └── search_tabs.py   # Extracted from ui/tabs.py
├── visualization/        # UMAP, DBSCAN, interactive plots  
│   └── latent_space.py  # Extracted from ui/latent_space.py
└── sidebar/             # Context-aware sidebar content
    └── context_sidebar.py # Extracted from ui/sidebar.py
```

### Integration Pattern
All screens use graceful component integration:
```python
try:
    from components.module import sophisticated_function
    sophisticated_function()  # Use advanced features
except ImportError as e:
    st.error(f"Component not integrated: {e}")
    fallback_function()  # Graceful degradation
```

### UI State Management
```
core/
├── app_state.py         # ✅ 3-screen state management
├── background_loader.py # ✅ Non-blocking progress tracking
└── session_manager.py   # ✅ Session state handling
```

## ⚠️ **URGENT: UI Integration Issues Post-Refactor**

**Status**: Performance optimization complete, UI components need updating  
**Priority**: High - Core 3-screen architecture works, but some UI components may be broken  
**Issue**: The recent performance refactor that fixed ScriptRunContext errors changed the core architecture significantly  
**Impact**: 
- ✅ App launches instantly (<1s) with zero errors  
- ✅ Background loading works perfectly  
- ⚠️ Some existing UI components may not work with new `core/` and `screens/` architecture  
- ⚠️ Original `ui/` components may need integration updates  

**Next Sprint Focus**: 
1. Test all UI components with new architecture
2. Update broken components to work with new state management  
3. Ensure all tabs and features work with the 3-screen flow
4. Polish user experience and fix any remaining issues

## 0. Environment Setup

- Use a Python virtual environment (`.venv`) for dependency isolation.
- Activate on Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- Activate on Unix/macOS: `source .venv/bin/activate`
- **Install CUDA-enabled PyTorch** for GPU acceleration. See the README for installation and troubleshooting instructions.
- If you see `torch.cuda.is_available() == False`, check your drivers and CUDA install, and ensure you have the correct PyTorch version for your CUDA toolkit.

## 1. Application Modes

- **Streamlit App (`app.py`)**: ⚡ **Lightning-fast startup** (<1s) with TRUE lazy loading. **NEW**: Unified 3-screen experience with sophisticated features integrated.
- **CLI MVP (`scripts/mvp_app.py`)**: Command-line tool for batch ingestion, embedding, captioning, and database creation. Optimized for large-scale, headless processing.

## 2. Core Modules & Directory Structure

- **config.py**: Global settings (e.g., GPU memory efficiency, model loading).
- **core/** (NEW): State management and background processing
  - `app_state.py`: 3-screen state management (Fast UI → Loading → Advanced UI)
  - `background_loader.py`: Non-blocking progress tracking with user-friendly phases
  - `session_manager.py`: Session state handling between screens
- **models/**
  - `clip_model.py`: CLIP model logic, including DNG/RAW support and batch processing.
  - `blip_model.py`: BLIP model logic for captioning.
  - `model_manager.py`: Loads and manages models for the Streamlit app.
  - `lazy_model_manager.py`: TRUE on-demand model loading with smart swapping.
- **metadata_extractor.py**: Extracts file metadata and image EXIF data.
- **database/**
  - `qdrant_connector.py`: QdrantDB class for all vector DB operations (batch upsert, search, collection management).
  - `db_manager.py`: Higher-level DB management for the Streamlit app.
  - `vector_db.py`: (Legacy, used by Streamlit app; new code uses `qdrant_connector.py`.)
- **screens/** (TRANSFORMED): 3-screen architecture
  - `fast_ui_screen.py`: ✅ Screen 1 - Simplified user-focused folder selection
  - `loading_screen.py`: ✅ Screen 2 - Engaging progress with excitement-building
  - `advanced_ui_screen.py`: ✅ Screen 3 - Sophisticated features with component integration
- **components/** (NEW): Organized extracted components
  - `search/search_tabs.py`: Text search, image search, AI games, duplicates (from ui/tabs.py)
  - `visualization/latent_space.py`: UMAP & DBSCAN with interactive plots (from ui/latent_space.py)
  - `sidebar/context_sidebar.py`: Context-aware sidebar content (from ui/sidebar.py)
- **ui/** (PRESERVED): Original sophisticated implementations for reference
  - Original components preserved but functionality extracted to `components/`
- **utils/**
  - `image_utils.py`: Image loading, resizing, preprocessing.
  - `logger.py**: Standardized logging.
  - `cuda_utils.py`: CUDA checks and memory usage logging.
  - `incremental_indexer.py`: File system watcher and incremental indexing logic.
  - `embedding_cache.py`: Cache for embedding computations.
  - `lazy_session_state.py`: TRUE lazy session management - UI state without model loading.
- **scripts/**
  - `mvp_app.py`: CLI MVP for batch processing.
  - `diagnose_cuda.py`: GPU diagnostics.
  - `minigame.py`: AI guessing game prototype.
  - `run_app.bat`: Windows launcher for the Streamlit app.

## 3. Data Flow

### A. Streamlit App (`app.py`) - ⚡ UNIFIED 3-SCREEN EXPERIENCE
1. **Screen 1 - Fast UI** (<1s startup):
   - User-focused folder selection with validation
   - Quick folder shortcuts (Pictures, Downloads, Desktop)
   - Welcoming messaging about AI capabilities
   - Background preparation starts silently

2. **Screen 2 - Loading Progress**:
   - Excitement-building progress messages by phase
   - Feature previews to build anticipation  
   - User-friendly time estimates
   - Collection celebration and encouraging facts

3. **Screen 3 - Advanced Features**:
   - Sophisticated search (text + image + AI games)
   - UMAP visualization with DBSCAN clustering
   - Duplicate detection and smart organization
   - Context-aware sidebar with advanced controls

### B. Component Integration Flow
1. **Graceful imports**: Each screen tries to import sophisticated components
2. **Fallback handling**: If components missing, shows user-friendly error + fallback
3. **Progressive enhancement**: Features work from basic to sophisticated levels
4. **State preservation**: Session state maintained across all screens

### C. CLI MVP (`scripts/mvp_app.py`)
1. User runs the script with a folder path.
2. Images are processed in batches:
   - CLIP embeddings (with DNG/RAW support)
   - BLIP captions (parallelized)
   - Metadata extraction
3. Batch upsert to Qdrant via `QdrantDB`.
4. Optionally outputs a summary (`results_summary.txt`) and a detailed CSV.

### D. Latent Space Explorer (`components/visualization/latent_space.py`)
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

## 8. File/Directory Structure (Current - Post Sprint 01)

```
project_root/
│
├── app.py                          # ⚡ Lightning-fast startup (<1s) + 3-screen flow
├── config.py
├── metadata_extractor.py
├── requirements.txt
├── test_lightning_startup.py       # 🔬 Performance verification testing
│
├── core/                           # 🆕 State management (Sprint 01)
│   ├── app_state.py               # 3-screen state transitions
│   ├── background_loader.py       # Non-blocking progress tracking
│   └── session_manager.py         # Session state handling
│
├── screens/                        # 🔄 TRANSFORMED (Sprint 01)
│   ├── fast_ui_screen.py          # ✅ Screen 1: Simplified & user-focused
│   ├── loading_screen.py          # ✅ Screen 2: Engaging progress experience  
│   └── advanced_ui_screen.py      # ✅ Screen 3: Sophisticated features
│
├── components/                     # 🆕 Extracted components (Sprint 01)
│   ├── search/
│   │   └── search_tabs.py         # Text search, AI games, duplicates
│   ├── visualization/
│   │   └── latent_space.py        # UMAP, DBSCAN, interactive plots
│   └── sidebar/
│       └── context_sidebar.py     # Context-aware sidebar content
│
├── models/
│   ├── clip_model.py
│   ├── blip_model.py
│   ├── model_manager.py
│   └── lazy_model_manager.py       # 🚀 TRUE on-demand model loading
│
├── database/
│   ├── qdrant_connector.py
│   ├── db_manager.py
│   └── vector_db.py
│
├── ui/                             # 📚 PRESERVED - Original implementations
│   ├── main_interface.py
│   ├── sidebar.py
│   ├── tabs.py
│   └── latent_space.py
│
├── utils/
│   ├── image_utils.py
│   ├── logger.py
│   ├── cuda_utils.py
│   ├── incremental_indexer.py
│   ├── embedding_cache.py
│   └── lazy_session_state.py       # ⚡ TRUE lazy session management
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
    ├── architecture.md             # 📖 This file (updated Sprint 01)
    ├── roadmap.md
    ├── CHANGELOG.md                # ✅ Updated with Sprint 01 achievements
    ├── SPRINT_STATUS.md            # 🆕 Sprint tracking
    └── sprints/                    # 🆕 Sprint documentation
        └── sprint-01/              # ✅ Complete Sprint 01 docs
            ├── PRD.md
            ├── technical-implementation-plan.md
            ├── completion-summary.md
            └── README.md
```

## 9. Sprint 01 Implementation Highlights

### Architecture Transformation
- **Before**: Fragmented dual UI system (`ui/` sophisticated + `screens/` basic)
- **After**: Unified 3-screen architecture with integrated sophisticated components

### Component Extraction Strategy
- Preserved ALL sophisticated functionality from `ui/` folder
- Organized into logical `components/` directory structure  
- Implemented graceful import patterns with fallback handling
- Maintained performance requirements (<1s startup)

### User Experience Evolution
- **Screen 1**: Removed technical metrics → User-focused welcome messaging
- **Screen 2**: Replaced boring logs → Excitement-building progress experience  
- **Screen 3**: Integrated real components → Sophisticated features with fallbacks

### Technical Achievements
- ✅ **Performance preserved**: <1s startup maintained throughout transformation
- ✅ **All features accessible**: Every sophisticated component integrated
- ✅ **Graceful error handling**: Fallbacks prevent broken experiences
- ✅ **Design compliance**: Matches UX_FLOW_DESIGN.md vision completely

---

**🎯 Next: Sprint 02 - Visual Design System**: With the unified architecture complete, Sprint 02 will focus on visual polish, smooth transitions, and mobile responsiveness.