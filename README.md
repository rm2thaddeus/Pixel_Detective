# Vibe Coding - A Hybrid Local/Cloud Media Search Engine

Vibe Coding is an advanced, locally-hosted search engine designed to index and search a personal media library using state-of-the-art AI models. It combines a high-performance backend with a (forthcoming) modern web interface to provide a seamless and powerful user experience.

## Project Status (June 2025)

-   **Current Focus**: Sprint 10 - [Critical UI Refactor](/docs/sprints/critical-ui-refactor/README.md)
-   **Last Major Milestone**: Completion of **Sprint 09**, which involved a significant backend overhaul.
-   **Summary of Sprint 09**:
    -   🚀 **High-Performance Backend**: The backend services were refactored for major performance gains, leveraging GPU optimization, dynamic batching, and asynchronous processing. The full technical details can be found in the [Backend Architecture Spec](/backend/ARCHITECTURE.md).
    -   ✅ **Persistent Vector Storage**: Integrated Qdrant for robust, persistent vector storage and search, with full support for creating and managing multiple collections.
    -   🗑️ **Legacy UI Deprecated**: The original Streamlit-based frontend has been completely removed, paving the way for a modern, scalable Next.js application.

## Core Features

-   **AI-Powered Search**: Use natural language or images to search your media library.
-   **Automatic Tagging & Captioning**: The system automatically generates descriptive captions and tags for your images using advanced models like CLIP and BLIP.
-   **High-Speed Ingestion**: A multi-threaded ingestion pipeline quickly processes large directories of images, extracts metadata, and generates embeddings.
-   **Local-First Architecture**: Your files and data stay on your machine. The application is designed to run locally, ensuring privacy and control.
-   **Scalable Vector Database**: Built on Qdrant, the system can handle hundreds of thousands of images with fast and accurate search results.

## Getting Started

> **Note**: The original Streamlit frontend has been removed. The following instructions are for running the backend services only. A new Next.js frontend is under development as part of the **Critical UI Refactor** sprint.

### Prerequisites

-   Python 3.9+
-   Docker and Docker Compose
-   NVIDIA GPU with CUDA installed (for GPU-accelerated inference)

### Installation & Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd Vibe-Coding
    ```

2.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Start Backend Services**: Use Docker Compose to launch the Qdrant vector database.
    ```bash
    docker-compose up -d
    ```

4.  **Run the FastAPI Applications**: Start the two backend services in separate terminals.

    *Terminal 1: ML Inference Service*
    ```bash
    uvicorn backend.ml_inference_fastapi_app.main:app --reload --port 8001
    ```

    *Terminal 2: Ingestion Orchestration Service*
    ```bash
    uvicorn backend.ingestion_orchestration_fastapi_app.main:app --reload --port 8002
    ```

Once the services are running, you can interact with them via the API endpoints documented in the backend `README.md` files.

## What's Next?

The project is currently focused on the **[Critical UI Refactor](/docs/sprints/critical-ui-refactor/README.md)** sprint, which will deliver a brand-new, high-performance frontend built with Next.js. This will replace the deprecated Streamlit UI and provide a modern, responsive, and feature-rich user experience for interacting with the powerful backend. 