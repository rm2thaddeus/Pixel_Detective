# Pixel Detective: AI-Powered Image Search

Pixel Detective is an advanced image search application that uses AI to analyze, caption, and search through your image collection. It combines multiple state-of-the-art AI models to provide a powerful and intuitive image search experience.

## 🔍 Key Features

- **AI-Powered Image Search**: Search your image collection using natural language queries
- **Automatic Image Captioning**: Generate high-quality captions for all your images using BLIP
- **Semantic Understanding**: Extract meaningful concepts and tags from your images using CLIP
- **Metadata Extraction**: Extract and index comprehensive metadata from various image formats
- **GPU Acceleration**: Optimized to run efficiently on consumer GPUs (6GB VRAM minimum recommended)
- **Interactive UI**: User-friendly Streamlit interface with multiple search modes

## 🧠 AI Models

Pixel Detective leverages two powerful AI models:

- **CLIP** (Contrastive Language-Image Pre-training): Creates embeddings that connect images and text in the same semantic space, enabling natural language search
- **BLIP** (Bootstrapping Language-Image Pre-training): Generates detailed captions for images, enhancing searchability and organization

## 📋 Requirements

The following packages are required to run this application:

```
qdrant-client
openai-clip
streamlit
rawpy
exifread
transformers==4.38.0
torch
torchvision
pillow
accelerate
bitsandbytes
```

You can install these dependencies by running:

```
pip install -r requirements.txt
```

## 🚀 Usage

1. Install the required dependencies
2. Run the Streamlit app:

```
streamlit run app.py
```

3. Enter the path to your image folder in the Command Center sidebar
4. Click "Launch the Brain Builder!" to process the images
5. Once processing is complete, use the tabs to:
   - **Text Search**: Find images using natural language queries
   - **Image Search**: Upload an image to find similar ones
   - **AI Guessing Game**: Test the AI's understanding of your images

## 📁 File Structure

- `app.py`: Main Streamlit application
- `config.py`: Configuration settings for the application
- `metadata_extractor.py`: Comprehensive metadata extraction from various image formats
- `vector_db.py`: Vector database operations for the main application
- `models/`
  - `clip_model.py`: CLIP model implementation for image embeddings and understanding
  - `blip_model.py`: BLIP model implementation for image captioning
- `database/`
  - `vector_db.py`: Qdrant vector database operations
- `ui/`
  - `tabs.py`: UI components for the different tabs
  - `sidebar.py`: UI components for the sidebar
- `utils/`
  - `image_utils.py`: Utility functions for image handling
  - `logger.py`: Logging configuration

## 🔧 GPU Optimization

The application is optimized to run efficiently on GPUs with at least 6GB of VRAM:

- Memory-efficient processing for large image collections
- Proper model loading and unloading to share GPU resources
- 8-bit quantization options for larger models
- Batch processing with configurable batch sizes

## 📝 Notes

- For large image collections, processing may take some time
- The application works best with JPEG, PNG, and other common image formats
- RAW and DNG file support depends on the availability of the `rawpy` library
- GPU acceleration significantly improves performance but is not required

## 📄 License

This project is open source and available under the MIT License. 