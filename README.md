# Pixel Detective - Dual AI Platform

> **Two Production-Ready AI Applications in One Repository**
> 
> **Pixel Detective**: AI-Powered Media Search Engine  
> **Dev Graph**: Temporal Knowledge Graph for Code Evolution

---

## 🎯 **Project Overview**

This repository showcases two distinct, production-ready AI applications built entirely through **AI-driven development** - every line of code was generated through prompts and AI collaboration.

### **🎨 Pixel Detective** - AI-Powered Media Search
A sophisticated, locally-hosted media search platform leveraging cutting-edge AI models (CLIP, BLIP) to provide intelligent search capabilities across personal media libraries.

### **🗺️ Dev Graph** - Temporal Knowledge Graph
A temporal semantic knowledge graph that tracks code evolution, linking git commits, code symbols, documentation, and requirements into an interactive visualization platform.

---

## 🚀 **Quick Start**

### **Prerequisites**
- **Docker & Docker Compose** (required)
- **Node.js 18+** and npm
- **Python 3.9+**
- **NVIDIA GPU with CUDA** (recommended for performance, but not required)

### **Launch Applications**

#### **Option 1: Pixel Detective (Media Search)**
```powershell
# Windows PowerShell
.\start_pixel_detective.ps1

# Windows CMD
start_pixel_detective.bat

# Linux/macOS
./start_pixel_detective.sh  # TODO: Create if needed
```

**Access:** http://localhost:3000

#### **Option 2: Dev Graph (Code Knowledge Graph)**
```powershell
# Windows PowerShell
.\start_dev_graph.ps1

# Windows CMD
start_dev_graph.bat

# Linux/macOS
./start_dev_graph.sh  # TODO: Create if needed
```

**Access:** http://localhost:3001

---

## 📊 **Pixel Detective** - Features & Architecture

### **Core Capabilities**
- ✨ **Natural Language Search** - "sunset over mountains"
- 🔍 **Visual Similarity Search** - Find images like a reference image
- 📝 **Automatic Captioning** - AI-generated image descriptions
- 🎯 **Latent Space Explorer** - Interactive UMAP clustering with DeckGL
- ⚡ **GPU-Accelerated Processing** - RAPIDS cuML for 10-300× speedups
- 📦 **Collection Management** - Organize media libraries

### **Technology Stack**
- **Frontend**: Next.js 14, TypeScript, Chakra UI, DeckGL
- **Backend**: FastAPI (3 microservices)
  - ML Inference (8001): CLIP/BLIP models
  - Ingestion Orchestration (8002): Collection management
  - GPU-UMAP Service (8003): RAPIDS cuML clustering
- **Database**: Qdrant vector database (6333)
- **AI Models**: CLIP (vision-language), BLIP (captioning)

### **Architecture Diagram**
```
┌─────────────────┐
│  Next.js UI     │  ← User Interface
│  (Port 3000)    │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬───────────┐
    │         │          │           │
┌───▼──┐  ┌──▼───┐  ┌───▼────┐  ┌──▼─────┐
│Ingest│  │  ML  │  │ UMAP   │  │Qdrant │
│8002  │  │ 8001 │  │ 8003   │  │ 6333  │
└──────┘  └──────┘  └────────┘  └────────┘
```

### **Performance Metrics**
- Sub-second search across 100K+ images
- GPU inference: 10× faster than CPU
- Real-time UMAP: 1K points < 3 seconds
- Memory efficient: < 100 MB frontend footprint

### **Key Use Cases**
1. **Personal Photo Library Search** - Natural language queries
2. **Visual Asset Management** - Find similar images
3. **Duplicate Detection** - Near-duplicate identification
4. **Content Organization** - Automatic clustering

---

## 🗺️ **Dev Graph** - Features & Architecture

### **Core Capabilities**
- 📈 **Temporal Code Evolution** - Track how code changes over time
- 🔗 **Semantic Linking** - Connect code, docs, and requirements
- 📊 **Sprint Analytics** - Map commits to development sprints
- 🎬 **WebGL Timeline** - CUDA-accelerated visualization
- 🔍 **Knowledge Graph Queries** - Neo4j-powered insights
- 📝 **Requirement Traceability** - Track implementation status

### **Technology Stack**
- **Frontend**: Next.js 14, TypeScript, Chakra UI, WebGL2
- **Backend**: FastAPI with Neo4j integration (8080)
- **Database**: Neo4j graph database (7687/7474)
- **Analysis**: 8-stage unified ingestion pipeline
- **Visualization**: DeckGL + Three.js for 3D rendering

### **Architecture Diagram**
```
                    ┌─────────────────┐
│ Dev Graph UI    │  ← Interactive Visualization
│ (Port 3001)     │
└────────┬────────┘
         │
    ┌────▼────────────┐
    │  Dev Graph API  │  ← FastAPI Backend
    │  (Port 8080)    │
    └────────┬────────┘
             │
        ┌────▼─────┐
        │  Neo4j   │  ← Graph Database
        │ 7687/7474│
        └──────────┘
```

### **Data Model**
- **Nodes**: GitCommit, File, Document, Chunk, Symbol, Library, Requirement, Sprint
- **Relationships**: TOUCHED, IMPLEMENTS, CONTAINS_CHUNK, MENTIONS, EVOLVES_FROM
- **Current Scale**: 30K+ nodes, 255K+ relationships

### **Key Use Cases**
1. **Code Evolution Analysis** - Understand how code changed
2. **Documentation Coverage** - Track code-to-docs links
3. **Sprint Retrospectives** - Analyze sprint metrics
4. **Requirement Tracing** - Track feature implementations
5. **Onboarding** - Visualize codebase structure

---

## 📁 **Repository Structure**

```
vibe-coding/
├── 🎨 Pixel Detective
│   ├── frontend/                    # Next.js UI (port 3000)
│   ├── backend/
│   │   ├── ingestion_orchestration_fastapi_app/  # Port 8002
│   │   ├── ml_inference_fastapi_app/             # Port 8001
│   │   └── gpu_umap_service/                     # Port 8003
│   └── start_pixel_detective.{ps1,bat}
│
├── 🗺️ Dev Graph
│   ├── tools/dev-graph-ui/          # Next.js UI (port 3001)
│   ├── developer_graph/             # FastAPI API (port 8080)
│   │   ├── api.py                   # Main app
│   │   ├── routes/                  # API endpoints
│   │   ├── temporal_engine.py       # Git ingestion
│   │   └── relationship_deriver.py  # Link discovery
│   ├── start_dev_graph.{ps1,bat}
│   └── dev_graph_audit/             # Analysis reports
│
├── 📚 Shared Resources
│   ├── docs/                        # Project documentation
│   │   ├── sprints/                 # Sprint planning & retrospectives
│   │   └── reference_guides/        # Technical guides
│   ├── utils/                       # Shared Python utilities
│   ├── database/                    # Database connectors
│   └── config.py                    # Global configuration
│
└── 🔧 DevOps
    ├── docker-compose.yml           # Service definitions
    ├── .cursor/rules/               # AI coding guidelines
    └── scripts/                     # Automation scripts
```

---

## 🛠️ **Development**

### **Environment Setup**

```bash
# 1. Clone repository
git clone https://github.com/yourusername/vibe-coding.git
cd vibe-coding

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env  # Configure Neo4j, Qdrant credentials

# 4. Launch desired application (see Quick Start)
```

### **Running Tests**

```bash
# Pixel Detective tests
pytest tests/ -v

# Dev Graph tests
pytest developer_graph/tests/ -v

# Integration tests
pytest tests/integration/ -v
```

### **Development Workflows**

#### **For Pixel Detective Development**
```bash
# Start backend services only
docker compose up -d qdrant_db
uvicorn backend.ingestion_orchestration_fastapi_app.main:app --reload --port 8002

# Start frontend in dev mode
cd frontend && npm run dev
```

#### **For Dev Graph Development**
```bash
# Start Neo4j only
docker compose up -d neo4j_db

# Start API in dev mode
uvicorn developer_graph.api:app --reload --port 8080

# Start UI in dev mode
cd tools/dev-graph-ui && npm run dev
```

---

## 📈 **Key Achievements**

### **Technical Excellence**
- ✅ **Dual Applications** - Two production-ready systems
- ✅ **Microservices Architecture** - Scalable, modular design
- ✅ **GPU Optimization** - 10-300× performance improvements
- ✅ **Modern Stack** - FastAPI, Next.js, Neo4j, Qdrant
- ✅ **AI Integration** - CLIP, BLIP, RAPIDS cuML
- ✅ **WebGL Visualization** - High-performance graphics
- ✅ **Docker Deployment** - Containerized services

### **Development Process**
- 🤖 **100% AI-Generated Code** - No manual coding
- 📝 **Prompt Engineering** - Sophisticated prompt strategies
- 🔄 **Iterative Refinement** - Continuous improvement
- 📊 **Comprehensive Documentation** - AI-generated docs
- 🧪 **Testing Strategy** - Automated test suites

---

## 📚 **Documentation**

### **Pixel Detective**
- [Backend Architecture](backend/ARCHITECTURE.md)
- [Frontend Architecture](frontend/ARCHITECTURE.md)
- [Ingestion API Docs](backend/ingestion_orchestration_fastapi_app/README.md)
- [ML Inference API Docs](backend/ml_inference_fastapi_app/README.md)
- [GPU-UMAP Service Docs](backend/gpu_umap_service/README.md)

### **Dev Graph**
- [Dev Graph Architecture](developer_graph/architecture.md)
- [Developer Guide](developer_graph/AGENTS.md)
- [Route Documentation](developer_graph/routes/AGENTS.md)
- [Migration Plan](docs/DEV_GRAPH_MIGRATION_PLAN.md)

### **Project-Wide**
- [Sprint Documentation](docs/sprints/)
- [Architecture Overview](Architecture.MD)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [Agent Guidelines](AGENTS.md)

---

## 🎨 **Portfolio Highlights**

This repository demonstrates:

### **Full-Stack Mastery**
- ✨ Modern frontend development (Next.js 14, React 18, TypeScript)
- 🚀 High-performance backends (FastAPI, async/await patterns)
- 🗄️ Database expertise (Neo4j, Qdrant, vector search)
- 🐳 DevOps & containerization (Docker, docker-compose)

### **AI/ML Expertise**
- 🤖 Production ML deployment (CLIP, BLIP, RAPIDS)
- ⚡ GPU optimization (CUDA, cuML, memory management)
- 📊 Vector embeddings & similarity search
- 🎯 Real-time inference pipelines

### **Advanced Concepts**
- 🔗 Knowledge graph engineering (Neo4j, temporal modeling)
- 🎨 WebGL/GPU visualization (DeckGL, Three.js)
- 🏗️ Microservices architecture (service orchestration)
- 📈 Performance optimization (caching, batching, parallelization)

### **Software Engineering**
- 📝 Comprehensive documentation
- 🧪 Test-driven development
- 🔄 CI/CD ready architecture
- 🎯 Production-grade code quality

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **Docker Services Won't Start**
```bash
# Check Docker is running
docker ps

# Reset Docker state
docker compose down
docker system prune -a

# Restart services
docker compose up -d
```

#### **Port Already in Use**
```bash
# Find process using port (Windows)
netstat -ano | findstr :8001

# Kill process
taskkill /PID <pid> /F
```

#### **GPU Not Detected**
```bash
# Check CUDA installation
nvidia-smi

# Verify Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### **Getting Help**
- 📖 Check documentation in `docs/`
- 🐛 Review troubleshooting guides in `.cursor/rules/`
- 💬 See AGENTS.md for development guidelines

---

## 📝 **License**

MIT License - see [LICENSE](LICENSE) file for details

---

## 🤝 **Contributing**

This repository demonstrates full AI-driven development. While contributions are welcome, please note the unique development process:

1. **Prompts over Code** - Describe desired changes in natural language
2. **AI Collaboration** - Use AI assistants to generate implementations
3. **Testing First** - Ensure comprehensive test coverage
4. **Documentation** - Update docs alongside code changes

---

## 🎯 **Project Status**

### **Pixel Detective**: ✅ Production Ready (Sprint 11 Complete)
- All core features implemented
- GPU acceleration operational
- Full test coverage
- Documentation complete

### **Dev Graph**: ✅ Standalone Ready (Sprint 11 Complete)
- 8-stage ingestion pipeline operational
- WebGL timeline visualization complete
- 30K+ nodes, 255K+ relationships indexed
- Migration playbook published

---

**🚀 Built with AI | 🎨 Powered by Prompts | 💡 Showcasing Modern Full-Stack Development**

*Two production-ready AI applications demonstrating the future of AI-assisted software development*
