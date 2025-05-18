# Pixel Detective: AI-Powered Image Search

Pixel Detective is an advanced image search application that uses AI to analyze, caption, and search through your image collection. It combines multiple state-of-the-art AI models to provide a powerful and intuitive image search experience.

## 🔍 Key Features

- **AI-Powered Image Search**: Search your image collection using natural language queries
- **Automatic Image Captioning**: Generate high-quality captions for all your images using BLIP
- **Semantic Understanding**: Extract meaningful concepts and tags from your images using CLIP
- **Metadata Extraction**: Extract and index comprehensive metadata from various image formats
- **GPU Acceleration**: Optimized to run efficiently on consumer GPUs (6GB VRAM minimum recommended)
- **Interactive UI**: User-friendly Streamlit interface with dark mode and extendable sidebar for images

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