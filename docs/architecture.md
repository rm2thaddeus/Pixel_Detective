# Architecture Overview

This document describes the high-level architecture of the Pixel Detective application, including core modules, data flow, and key components.

## 0. Environment Setup
- Use a Python virtual environment (`.venv`) for dependency isolation.
- Activate on Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- Activate on Unix/macOS: `source .venv/bin/activate`
- **Install CUDA-enabled PyTorch** for GPU acceleration. See the README for installation and troubleshooting instructions. If you see `torch.cuda.is_available() == False`, check your drivers and CUDA install, and ensure you have the correct PyTorch version for your CUDA toolkit.

## 1. Streamlit Frontend

- **app.py**: Entry point for the Streamlit app. Initializes environment variables, loads CSS, configures the page and sidebar, and orchestrates component rendering.
- **ui/**:
  - **main_interface.py**: Coordinates layout and renders the main tabs (Text Search, Image Search, AI Guessing Game).
  - **sidebar.py**: Implements the sidebar controls and file selection UI.
  - **tabs.py**: Defines the content and interactions for each tab.

## 2. Configuration

- **config.py**: Holds global settings such as `GPU_MEMORY_EFFICIENT` and `KEEP_MODELS_LOADED`.

## 3. Model Management

- **models/model_manager.py**: Loads and manages AI models (CLIP and BLIP) with device selection and optional quantization.

## 4. Data Extraction & Processing

- **metadata_extractor.py**: Extracts file metadata and image EXIF data.
- **vector_db.py**: Generates and queries embeddings against the Qdrant vector database.
- **database/db_manager.py**: Wraps vector database operations with higher-level management logic.

## 5. Utilities

- **utils/image_utils.py**: Helper functions for image loading, resizing, and preprocessing.
- **utils/logger.py**: Configures and provides a standardized logger instance.
- **utils/cuda_utils.py**: Checks for CUDA availability and logs memory usage statistics.

## 6. Scripts & Prototypes

- **scripts/**: Contains auxiliary scripts and prototypes for development:
  - `run_app.bat`: Windows startup script for the Streamlit app.
  - `diagnose_cuda.py`: Checks GPU availability and memory.
  - `pipeline.py`: Batch processing pipeline for image ingestion.
  - `embedding.py`: Standalone embedding generation utility.
  - `minigame.py`: AI guessing game prototype.
  - `mvp_app.py`: Minimal viable product Streamlit prototype.

## 7. Static Assets & Test Data

- **static/**: Static assets served by the app (CSS, icons).
- **assets/**: Additional resources (e.g., images, models).
- **docs/test_data/**: Sample data for demos and testing.

## 8. Runtime Flow

1. User uploads or points to an image folder via the Streamlit sidebar.
2. `ModelManager` loads AI models (CLIP, BLIP) and generates embeddings.
3. `MetadataExtractor` processes images to extract metadata.
4. `DatabaseManager` stores embeddings and metadata in Qdrant.
5. The UI queries `DatabaseManager` to display search results, image comparisons, and game interactions.

## 9. Deployment & Scaling

- The app is designed to run on consumer GPUs (6GB VRAM minimum) but falls back to CPU.
- Batch processing and 8-bit quantization help reduce memory footprint for large collections.
- Qdrant provides scalable vector storage for growing image datasets.

## RAW/DNG Image Support
Pixel Detective now supports DNG (RAW) images. When a DNG file is encountered, it is loaded using rawpy and converted to a standard RGB image before being processed by the CLIP and BLIP models. This ensures seamless integration of RAW files into the embedding and captioning pipeline.

## Results Summary Output (Optional)
The batch processing script can optionally print and save a summary of all processed images, their captions, and embedding status to `results_summary.txt` by using the `--save-summary` flag. This is intended for debugging and is off by default. 