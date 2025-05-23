# Pixel Detective: AI-Powered Image Search

Pixel Detective is an advanced image search application that uses AI to analyze, caption, and search through your image collection. It combines multiple state-of-the-art AI models to provide a powerful and intuitive image search experience.

## �� Key Features

- **Advanced Hybrid Search**: Combines semantic vector search with metadata filtering using Qdrant's Query API
  - Natural language queries (e.g., "happy family photos")
  - Metadata-aware search (e.g., "camera:canon iso:100")
  - Soft constraint filtering that boosts relevance without restricting results
  - RRF (Reciprocal Rank Fusion) for optimal result ranking
- **AI-Powered Image Search**: Search your image collection using natural language queries
- **Automatic Image Captioning**: Generate high-quality captions for all your images using BLIP
- **Semantic Understanding**: Extract meaningful concepts and tags from your images using CLIP
- **Comprehensive Metadata Extraction**: Extract and index 80+ metadata fields from EXIF/XMP data
  - Camera settings (aperture, ISO, focal length, etc.)
  - Geographic information (GPS coordinates, location names)
  - Temporal data (dates taken, modified, digitized)
  - Technical details (color temperature, white balance, flash settings)
  - Custom tags and keywords
- **RAW/DNG Support**: Full support for DNG (RAW) images. DNG files are processed for both CLIP embeddings and BLIP captions using rawpy and PIL interoperability.
- **GPU Acceleration**: Optimized to run efficiently on consumer GPUs (6GB VRAM minimum recommended)
- **Interactive UI**: User-friendly Streamlit interface with dark mode and extendable sidebar for images
- **Latent Space Explorer**: Visualize image embeddings in 2D using UMAP and a robust, minimal scatter plot. The current implementation uses a single, reliable plotly.graph_objects scatter plot for maximum reliability. Previous attempts at lasso/selection and advanced coloring led to invisible points and UI bugs due to subtle Plotly/Streamlit interactions. If you encounter invisible points, start with a minimal plot and add features incrementally.

## 🔍 Enhanced Search Capabilities

Pixel Detective features a sophisticated hybrid search system that intelligently combines:

1. **Vector Similarity Search**: Semantic understanding of image content using CLIP embeddings
2. **Metadata Filtering**: Precise filtering based on extracted EXIF/XMP metadata
3. **Query Intelligence**: Automatic parsing of complex queries like "sunset photos taken with Canon in 2023"

**Example Queries:**
- `"happy family"` - Semantic search for family photos
- `"camera:canon"` - All photos taken with Canon cameras  
- `"iso:100 aperture:2.8"` - Technical specifications
- `"strasbourg 2023"` - Location and time-based search
- `"landscape sunset"` - Combined semantic and descriptive search

The system uses SHOULD-based logic, meaning queries return relevant results even when specific metadata constraints aren't perfectly matched, ensuring you always discover relevant images.

## 🧠 AI Models

Pixel Detective leverages two powerful AI models:

- **CLIP** (Contrastive Language-Image Pre-training): Creates embeddings that connect images and text in the same semantic space, enabling natural language search
- **BLIP** (Bootstrapping Language-Image Pre-training): Generates detailed captions for images, enhancing searchability and organization

## 📋 Requirements

**Recommended**: Create and activate a Python virtual environment for dependency isolation before installing dependencies:

```
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Unix/macOS
source .venv/bin/activate
```

**Install CUDA-enabled PyTorch (required for GPU acceleration):**

- Visit https://pytorch.org/get-started/locally/ and select your CUDA version (e.g., CUDA 11.8)
- Example for CUDA 11.8:
```
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```
- After install, verify with:
```
python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"
```
- You should see a version like `2.7.0+cu118`, a CUDA version string, and `True` for CUDA availability.

**Troubleshooting:**
- If you see `torch.cuda.is_available() == False`, check your NVIDIA drivers and CUDA installation, and ensure you installed the correct PyTorch version for your CUDA toolkit.
- If you run out of disk space, clear your pip cache with `pip cache purge`.

**Qdrant Vector Database Required for Metadata-Based Filtering and Hybrid Search:**
- For advanced search features (metadata-based filtering, hybrid vector+metadata search), you must have the Qdrant vector database running locally or remotely. The easiest way is via Docker:
```
docker run -p 6333:6333 qdrant/qdrant
```
- If Qdrant is not running, these features will not work and you may see errors or missing results in the UI.

The following packages are required to run this application (see `docs/current_requirements.txt` for full list):

```
torch==2.7.0+cu118
torchvision==0.22.0+cu118
torchaudio==2.7.0+cu118
# ...
```

## 🚀 Usage Example (Non-Interactive Script)

To run the MVP batch processing script non-interactively, use command-line arguments:

```
python scripts/mvp_app.py --folder "C:\Users\aitor\OneDrive\Escritorio\test images" --batch-size 16 --max-workers 4 --query "a cat"
```

- `--folder` (required): Path to the image folder
- `--batch-size` (optional): Batch size for CLIP embeddings (default: 16)
- `--max-workers` (optional): Number of parallel workers for BLIP captions (default: 4)
- `--query` (optional): Text query for image search (if omitted, search is skipped)

After processing, a summary of all images, their captions, and embedding status is printed to the console and saved to `results_summary.txt` in the project root.

To print and save a summary of all images, their captions, and embedding status to `results_summary.txt`, use the optional `--save-summary` flag. This is intended for debugging and is off by default.

Example:
```
python scripts/mvp_app.py --folder "C:\path\to\images" --save-summary
```