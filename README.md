<!-- Sprint-11 requirements summary:
Functional: interactive latent-space explorer with clustering (DBSCAN, K-Means, Hierarchical), lasso selection → collection workflow, thumbnail previews, and cluster quality metrics.
Non-functional: <3 s load for 1 k points on GPU, accessibility ≥90 %, responsive mobile layout, memory <100 MB.
-->
# Pixel Detective - AI-Powered Media Search Engine

A sophisticated, locally-hosted media search platform that leverages cutting-edge AI models to provide intelligent search capabilities across personal media libraries. Built with a modern microservices architecture featuring FastAPI backends and a Next.js frontend.

## 🎯 Project Overview
Pixel Detective is a vibe coding manifesto: every aspect of this project was created through a process of idea generation, prompt engineering, and AI-driven software synthesis—no hand-written code, just pure concept-to-execution via prompts.

### Key Achievements
- **🚀 Complete Architecture Refactor** - Migrated from monolithic to microservices architecture
- **⚡ High-Performance Backend** - GPU-optimized ML inference with dynamic batching
- **🎨 Modern Frontend** - React/Next.js application with Chakra UI
- **📊 Vector Database Integration** - Qdrant for persistent, scalable vector storage
- **🔧 DevOps Pipeline** - Docker containerization and MCP server integration
- **🗺️ Interactive Latent Space Explorer** - Real-time UMAP scatter plot with clustering, lasso selection & thumbnail previews
- **⚡ GPU-Accelerated UMAP & Clustering** - Dedicated RAPIDS cuML micro-service delivering 10-300× speed-ups

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Next.js       │    │   FastAPI        │    │   Qdrant        │
│   Frontend      │◄──►│   Backend        │◄──►│   Vector DB     │
│                 │    │                  │    │                 │
│ • React/TS      │    │ • ML Inference   │    │ • Vector Search │
│ • Chakra UI     │    │ • Orchestration  │    │ • Collections   │
│ • State Mgmt    │    │ • GPU Optimize   │    │ • Persistence   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## ✨ Core Features

### AI-Powered Search
- **Natural Language Queries** - Search using descriptive text
- **Visual Similarity** - Find images using reference images  
- **Automatic Captioning** - BLIP model generates descriptions
- **Semantic Embeddings** - CLIP model for deep understanding

### High-Performance Processing
- **GPU Acceleration** - CUDA-optimized inference pipeline
- **Batch Processing** - Efficient handling of large image sets
- **Async Operations** - Non-blocking UI with background processing
- **Memory Management** - Smart model loading/unloading

### Modern Web Interface
- **Responsive Design** - Mobile-first, accessible UI
- **Real-time Updates** - Live progress tracking and notifications
- **Collection Management** - Organize and manage image collections
- **Advanced Filtering** - Metadata-based search refinement

## 🛠️ Technology Stack

### Backend
- **FastAPI** - High-performance async web framework
- **PyTorch** - Deep learning model inference
- **Qdrant** - Vector similarity search database
- **Docker** - Containerized deployment

### Frontend  
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Chakra UI** - Modern component library
- **Zustand** - Lightweight state management

### AI/ML Models
- **CLIP** - Vision-language understanding
- **BLIP** - Image captioning
- **Custom Pipelines** - Optimized inference workflows

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm
- Python 3.9+
- Docker & Docker Compose
- NVIDIA GPU with CUDA (recommended)

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/vibe-coding.git
cd vibe-coding
```

2. Follow one of the workflows below:

Choose one of the following workflows depending on your environment:

**A) One-click Dev Stack (Windows / WSL 2)**

```powershell
# From the repo root
scripts\start_dev.bat
```

This script launches and hot-reloads the complete stack:
1. **Qdrant** vector database (6333)
2. **GPU-UMAP micro-service** – FastAPI + RAPIDS cuML (8001)
3. **Ingestion Orchestration API** – FastAPI (8002)
4. **ML Inference API** – FastAPI (8003)
5. **Next.js Frontend** – auto-opened at http://localhost:3000

**B) Manual / Linux / macOS**

```bash
# Spin up core infrastructure
docker compose up -d qdrant gpu-umap

# Backend services (hot-reload)
uvicorn backend.ingestion_orchestration_fastapi_app.main:app --port 8002 --reload &
uvicorn backend.ml_inference_fastapi_app.main:app --port 8003 --reload &

# Frontend
cd frontend
npm install
npm run dev
```

Access points:
* Frontend → http://localhost:3000  
* Ingestion API docs → http://localhost:8002/docs  
* GPU-UMAP docs → http://localhost:8001/docs

## 📈 Performance Highlights

- **Sub-second search** across 100K+ images
- **GPU-optimized inference** with 10x speed improvement
- **Concurrent processing** of multiple collections
- **Memory-efficient** model management
- **Real-time latent-space rendering** – 1 k+ point UMAP projection <3 s on consumer GPUs
- **Real-time progress** tracking and updates

## 📚 Documentation

- [Backend Architecture](/backend/ARCHITECTURE.md)
- [Frontend Architecture](/frontend/ARCHITECTURE.md)  
- [Sprint Documentation](/docs/sprints/)
   - [Sprint 11 Overview](/docs/sprints/sprint-11/README.md)
   - [Sprint 11 PRD](/docs/sprints/sprint-11/PRD.md)
   - [Sprint 11 Technical Plan](/docs/sprints/sprint-11/technical-implementation-plan.md)
   - [Sprint 11 Quick Reference](/docs/sprints/sprint-11/QUICK_REFERENCE.md)
   - [CUDA Acceleration Guide](/docs/sprints/sprint-11/CUDA_ACCELERATION_GUIDE.md)
- [API Reference](/backend/ingestion_orchestration_fastapi_app/README.md)

## 🎨 Portfolio Highlights

This project demonstrates:
- **Full-Stack Expertise** - End-to-end application development
- **AI/ML Integration** - Production-ready ML model deployment
- **Modern Architecture** - Microservices, containers, and scalability
- **Performance Optimization** - GPU acceleration and efficient algorithms
- **User Experience** - Intuitive interface design and responsive development

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Built with ❤️ showcasing modern full-stack development with AI integration* 