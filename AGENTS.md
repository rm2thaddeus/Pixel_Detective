# AI Agent Guidelines - Vibe Coding Project

## 🎯 **Overview**

This document provides comprehensive guidelines for AI agents working on the Vibe Coding project, which consists of two production-ready applications:

1. **Pixel Detective** - AI-powered media search engine
2. **Dev Graph** - Temporal knowledge graph for code evolution

**Key Principle**: This entire codebase was built through AI-assisted development. Every change should maintain this philosophy and code quality standards.

---

## 📋 **Quick Reference**

### **When to Use Which Documentation**

| Task | Primary Document | Secondary Documents |
|------|-----------------|-------------------|
| **Understanding Project** | README.md, Architecture.MD | This file (AGENTS.md) |
| **Working on Pixel Detective** | backend/ARCHITECTURE.md, frontend/ARCHITECTURE.md | backend/*/README.md |
| **Working on Dev Graph** | developer_graph/architecture.md, developer_graph/AGENTS.md | developer_graph/routes/AGENTS.md |
| **Backend Development** | .cursor/rules/backend/* | Backend service READMEs |
| **Frontend Development** | .cursor/rules/frontend/* | frontend/ARCHITECTURE.md |
| **Deployment** | Start scripts, docker-compose.yml | This file (Deployment section) |
| **Debugging** | .cursor/rules/debugging.mdc | Service-specific docs |
| **Sprint Planning** | .cursor/rules/sprint-planning.mdc | docs/sprints/ |

---

## 🏗️ **Repository Structure**

### **Root Level Files**

```
vibe-coding/
├── README.md                          # Project overview (read first!)
├── Architecture.MD                    # Complete architecture
├── AGENTS.md                          # This file - agent guidelines
├── DEVELOPER_GUIDE.md                 # Developer onboarding
├── docker-compose.yml                 # Service definitions
├── requirements.txt                   # Python dependencies
├── config.py                          # Global configuration
│
├── start_pixel_detective.{ps1,bat}   # Launch Pixel Detective
├── start_dev_graph.{ps1,bat}         # Launch Dev Graph
│
└── .cursor/rules/                     # AI coding guidelines
    ├── projectrules.mdc              # Master rules
    ├── auto-activation-config.mdc    # Rule activation patterns
    ├── smart-entry-points.mdc        # Navigation guide
    ├── backend/                       # Backend-specific rules
    ├── frontend/                      # Frontend-specific rules
    └── sprint-lessons-learned.mdc    # Critical lessons
```

### **Application Directories**

#### **Pixel Detective**
```
├── frontend/                          # Next.js UI (port 3000)
│   ├── src/app/                      # App router pages
│   ├── src/components/               # React components
│   ├── src/lib/                      # Utilities & API client
│   └── ARCHITECTURE.md               # Frontend architecture
│
└── backend/
    ├── ingestion_orchestration_fastapi_app/   # Port 8002
    ├── ml_inference_fastapi_app/              # Port 8001
    └── gpu_umap_service/                      # Port 8003
```

#### **Dev Graph**
```
├── tools/dev-graph-ui/               # Next.js UI (port 3001)
│   ├── src/app/                      # App router pages
│   └── src/components/               # React components
│
└── developer_graph/                  # FastAPI API (port 8080)
    ├── api.py                        # Main app
    ├── routes/                       # API endpoints
    ├── temporal_engine.py            # Git ingestion
    ├── relationship_deriver.py       # Link discovery
    ├── AGENTS.md                     # Dev Graph guidelines
    └── architecture.md               # Dev Graph architecture
```

---

## 🚀 **Getting Started as an AI Agent**

### **Step 1: Understand the Project**

1. **Read** `README.md` - Get project overview
2. **Scan** `Architecture.MD` - Understand system design
3. **Review** this file (`AGENTS.md`) - Learn conventions

### **Step 2: Identify Your Task Context**

| If User Asks About... | Navigate To... |
|----------------------|----------------|
| Media search, images, collections, CLIP, BLIP | Pixel Detective section |
| Git history, code evolution, knowledge graph, Neo4j | Dev Graph section |
| Backend APIs, FastAPI, services | Backend section |
| Frontend UI, React, Next.js | Frontend section |
| Deployment, Docker, setup | Deployment section |
| Testing, debugging | Testing section |

### **Step 3: Follow Applicable Rules**

The `.cursor/rules/` directory contains context-specific guidelines:

- **Always applicable**: `projectrules.mdc`
- **Backend work**: `.cursor/rules/backend/*.mdc`
- **Frontend work**: `.cursor/rules/frontend/*.mdc`
- **Debugging**: `.cursor/rules/debugging.mdc`
- **Sprint work**: `.cursor/rules/sprint-planning.mdc`

### **Step 4: Make Changes**

1. **Read existing code** - Understand patterns
2. **Follow conventions** - Match existing style
3. **Update tests** - Ensure coverage
4. **Update docs** - Keep documentation current

---

## 🎨 **Pixel Detective - Agent Guidelines**

### **Core Concepts**

**Purpose**: AI-powered media search using CLIP embeddings and BLIP captions.

**Key Technologies**:
- Frontend: Next.js 14, Chakra UI, DeckGL
- Backend: FastAPI (3 microservices)
- Database: Qdrant (vector search)
- AI Models: CLIP, BLIP, RAPIDS cuML

### **Common Tasks**

#### **Adding Features to Search**
1. **Backend**: Modify `backend/ingestion_orchestration_fastapi_app/routers/search.py`
2. **Frontend**: Update `frontend/src/app/search/page.tsx`
3. **API Client**: Extend `frontend/src/lib/api.ts`
4. **Tests**: Add to `tests/`

#### **Modifying Ingestion Pipeline**
1. **Main Logic**: `backend/ingestion_orchestration_fastapi_app/pipeline/manager.py`
2. **ML Calls**: `backend/ml_inference_fastapi_app/routers/inference.py`
3. **Qdrant Ops**: `backend/ingestion_orchestration_fastapi_app/routers/collections.py`

#### **Improving ML Performance**
1. **Model Loading**: `backend/ml_inference_fastapi_app/main.py` (lifespan)
2. **Batch Processing**: Follow patterns in `backend/ml_inference_fastapi_app/routers/inference.py`
3. **GPU Management**: See `.cursor/rules/backend/ml-service-integration.mdc`

#### **UI/UX Changes**
1. **Components**: `frontend/src/components/`
2. **Layouts**: `frontend/src/app/layout.tsx`
3. **Styling**: Use Chakra UI tokens consistently
4. **State**: React Query for server state, Zustand for UI state

### **Architecture Patterns to Follow**

#### **Backend**
- ✅ **Dependency Injection** - Use `Depends()`, never circular imports
- ✅ **Async Operations** - All I/O is async
- ✅ **Background Jobs** - Use `BackgroundTasks` for long operations
- ✅ **Error Handling** - Structured errors with codes
- ✅ **GPU Locks** - Exclusive access with `asyncio.Lock()`

See: `.cursor/rules/backend/*.mdc` for detailed patterns

#### **Frontend**
- ✅ **React Query** - All API calls through useQuery/useMutation
- ✅ **Chakra UI** - Use design system components
- ✅ **TypeScript** - Full type safety
- ✅ **Error Boundaries** - Wrap risky components
- ✅ **Loading States** - Handle all async states

See: `.cursor/rules/frontend/*.mdc` for detailed patterns

### **Testing Strategy**

```bash
# Backend tests
pytest backend/ingestion_orchestration_fastapi_app/tests/
pytest backend/ml_inference_fastapi_app/tests/

# Frontend tests
cd frontend && npm test

# Integration tests
pytest tests/integration/
```

### **Debugging Checklist**

- [ ] Check service health endpoints: `/health`
- [ ] Verify Qdrant connection: `http://localhost:6333/dashboard`
- [ ] Check Docker containers: `docker ps`
- [ ] Review logs: Check PowerShell windows
- [ ] Test API directly: Use FastAPI `/docs` interface

---

## 🗺️ **Dev Graph - Agent Guidelines**

### **Core Concepts**

**Purpose**: Temporal knowledge graph tracking code evolution over git history.

**Key Technologies**:
- Frontend: Next.js 14, WebGL2, DeckGL
- Backend: FastAPI + Neo4j
- Database: Neo4j (graph database)
- Analysis: 8-stage ingestion pipeline

### **Common Tasks**

#### **Modifying Ingestion Pipeline**
1. **Unified Pipeline**: `developer_graph/routes/unified_ingest.py`
2. **Temporal Engine**: `developer_graph/temporal_engine.py`
3. **Symbol Extraction**: `developer_graph/code_symbol_extractor.py`
4. **Relationship Logic**: `developer_graph/relationship_deriver.py`

#### **Adding New Graph Queries**
1. **Create Route**: `developer_graph/routes/` (follow existing patterns)
2. **Neo4j Queries**: Use Cypher with proper error handling
3. **API Models**: Define Pydantic models for request/response
4. **Documentation**: Update AGENTS.md

#### **Timeline Visualization Changes**
1. **WebGL Renderer**: `tools/dev-graph-ui/src/app/dev-graph/timeline/`
2. **Data Fetching**: `tools/dev-graph-ui/src/lib/api.ts`
3. **Performance**: Mind the node budget (adaptive LOD)

#### **Data Quality Improvements**
1. **Audit System**: `developer_graph/routes/quality.py`
2. **Validation**: `developer_graph/data_validator.py`
3. **Reports**: Generated in `dev_graph_audit/`

### **Architecture Patterns to Follow**

#### **Backend**
- ✅ **Neo4j Sessions** - Use context managers `with driver.session():`
- ✅ **Batch Operations** - UNWIND for bulk creates
- ✅ **Cypher Best Practices** - Indexed lookups, MERGE for deduplication
- ✅ **Error Handling** - Handle Neo4j exceptions gracefully
- ✅ **Incremental Updates** - Use watermarks for delta processing

See: `developer_graph/AGENTS.md` for Dev Graph-specific patterns

#### **Frontend**
- ✅ **WebGL Performance** - LOD, culling, budget management
- ✅ **State Management** - React Query for graph data
- ✅ **Responsive Design** - Handle large graphs gracefully
- ✅ **Accessibility** - Keyboard navigation, ARIA labels

### **Data Model Guidelines**

#### **Adding New Node Types**
1. Define in `developer_graph/models.py`
2. Add schema constraints in `developer_graph/schema/temporal_schema.py`
3. Update ingestion in appropriate stage
4. Add queries in `developer_graph/routes/`

#### **Adding New Relationships**
1. Define relationship semantics clearly
2. Consider directionality (from→to)
3. Add properties for timestamps, evidence
4. Update relationship deriver if needed

### **Testing Strategy**

```bash
# Backend tests
pytest developer_graph/tests/

# Integration tests
pytest tests/test_dev_graph_integration.py

# Data quality checks
curl http://localhost:8080/api/v1/dev-graph/audit
```

### **Debugging Checklist**

- [ ] Check Neo4j connection: `http://localhost:7474`
- [ ] Verify API health: `http://localhost:8080/api/v1/dev-graph/health`
- [ ] Run audit: `POST /api/v1/dev-graph/audit`
- [ ] Check ingestion logs in API window
- [ ] Query Neo4j directly in browser

---

## 🔧 **Development Workflows**

### **Starting Development Environment**

#### **For Pixel Detective Work**
```powershell
# Full stack
.\start_pixel_detective.ps1

# Or individual services
docker compose up -d qdrant_db
uvicorn backend.ingestion_orchestration_fastapi_app.main:app --reload --port 8002
cd frontend && npm run dev
```

#### **For Dev Graph Work**
```powershell
# Full stack
.\start_dev_graph.ps1

# Or individual services
docker compose up -d neo4j_db
uvicorn developer_graph.api:app --reload --port 8080
cd tools/dev-graph-ui && npm run dev
```

### **Making Code Changes**

#### **Backend Changes**
1. **Identify service**: Ingestion, ML, UMAP, or Dev Graph
2. **Read existing code**: Understand patterns
3. **Follow dependency injection**: Use `Depends()`
4. **Add tests**: Cover new functionality
5. **Update docs**: README or AGENTS.md
6. **Test locally**: Hit `/docs` endpoint

#### **Frontend Changes**
1. **Identify component**: Layout, page, or component
2. **Check existing patterns**: Match code style
3. **Use React Query**: For API calls
4. **Follow Chakra UI**: Use design system
5. **Test responsively**: Check mobile view
6. **Update types**: Keep TypeScript happy

### **Adding New Features**

#### **Feature Development Checklist**
- [ ] **Design**: Sketch out data flow and UI
- [ ] **Backend API**: Define endpoints and models
- [ ] **Database**: Add any new schema requirements
- [ ] **Frontend**: Implement UI components
- [ ] **Integration**: Connect frontend to backend
- [ ] **Testing**: Unit and integration tests
- [ ] **Documentation**: Update relevant docs
- [ ] **Performance**: Profile and optimize

#### **Code Review Checklist**
- [ ] **Follows patterns**: Matches existing code style
- [ ] **Type safe**: TypeScript/Python types correct
- [ ] **Error handling**: Graceful degradation
- [ ] **Performance**: No obvious bottlenecks
- [ ] **Security**: Input validation, no SQL injection
- [ ] **Tests**: Adequate coverage
- [ ] **Documentation**: Clear and complete

---

## 🐛 **Debugging & Troubleshooting**

### **Common Issues**

#### **Services Won't Start**
1. **Check Docker**: `docker ps` - are containers running?
2. **Check ports**: `netstat -ano | findstr :8001` - port conflicts?
3. **Check logs**: Review PowerShell window outputs
4. **Restart services**: `docker compose down && docker compose up -d`

#### **Frontend Build Errors**
1. **Clear cache**: `rm -rf .next` and `rm -rf node_modules`
2. **Reinstall**: `npm install`
3. **Check types**: `npm run type-check`
4. **Check lint**: `npm run lint`

#### **Backend API Errors**
1. **Check health**: `curl http://localhost:8002/health`
2. **Review logs**: Check FastAPI console output
3. **Test endpoints**: Use `/docs` Swagger UI
4. **Check database**: Verify Qdrant/Neo4j connection

#### **GPU Issues**
1. **Verify CUDA**: `nvidia-smi`
2. **Check Docker GPU**: `docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`
3. **Fallback to CPU**: Services should auto-detect and fallback
4. **Memory issues**: Reduce batch sizes

### **Debugging Tools**

- **FastAPI /docs**: Interactive API testing
- **React DevTools**: Component inspection
- **Network Tab**: API request inspection
- **Docker logs**: `docker logs <container_id>`
- **Neo4j Browser**: Graph query testing
- **Qdrant Dashboard**: Vector DB inspection

---

## 📚 **Documentation Standards**

### **Code Comments**

#### **Python (Backend)**
```python
def process_batch(items: List[Item], batch_size: int = 32) -> List[Result]:
    """Process items in batches for efficiency.
    
    Args:
        items: List of items to process
        batch_size: Number of items per batch (default: 32)
        
    Returns:
        List of processing results
        
    Raises:
        ProcessingError: If batch processing fails
        
    Example:
        >>> results = process_batch(items, batch_size=16)
    """
```

#### **TypeScript (Frontend)**
```typescript
/**
 * Fetch collections from the API with optional filtering
 * 
 * @param filters - Optional filter parameters
 * @returns Promise resolving to collection list
 * @throws {ApiError} If API request fails
 * 
 * @example
 * const collections = await fetchCollections({ active: true });
 */
async function fetchCollections(filters?: CollectionFilters): Promise<Collection[]> {
```

### **README Updates**

When adding new features, update:
1. **Root README.md** - If feature is major
2. **Service README.md** - Specific service changes
3. **Architecture.MD** - If architecture changes
4. **AGENTS.md** - If workflow changes

### **Commit Messages**

Follow conventional commits:
```
feat(pixel-detective): add image similarity search
fix(dev-graph): resolve Neo4j connection timeout
docs(readme): update deployment instructions
perf(ml-inference): optimize CLIP batch processing
refactor(frontend): extract search components
test(ingestion): add integration tests
chore(deps): update dependencies
```

---

## 🎯 **Best Practices**

### **Code Quality**

#### **Backend (Python/FastAPI)**
- ✅ Use type hints everywhere
- ✅ Follow PEP 8 style guide
- ✅ Async/await for I/O operations
- ✅ Dependency injection pattern
- ✅ Comprehensive error handling
- ✅ Pydantic models for validation
- ✅ Structured logging

#### **Frontend (TypeScript/React)**
- ✅ Strict TypeScript configuration
- ✅ React hooks best practices
- ✅ Component composition
- ✅ React Query for server state
- ✅ Chakra UI design system
- ✅ Responsive design patterns
- ✅ Accessibility (WCAG AA)

### **Performance**

#### **Backend Optimization**
- 🚀 Batch operations (UNWIND in Neo4j, bulk upsert in Qdrant)
- 🚀 GPU locking for exclusive access
- 🚀 Memory-efficient streaming
- 🚀 Connection pooling
- 🚀 Caching (disk cache, embedding cache)
- 🚀 Async processing

#### **Frontend Optimization**
- 🚀 Code splitting (Next.js automatic)
- 🚀 Image optimization (Next.js Image)
- 🚀 Virtual scrolling for large lists
- 🚀 WebGL for complex visualizations
- 🚀 React Query caching
- 🚀 Lazy loading components

### **Security**

- 🔐 Input validation (Pydantic, Zod)
- 🔐 Parameterized queries (prevent injection)
- 🔐 Error message sanitization
- 🔐 Rate limiting (future: implement)
- 🔐 Authentication (future: implement)
- 🔐 HTTPS in production

---

## 📖 **Reference Links**

### **Primary Documentation**
- [README.md](README.md) - Project overview
- [Architecture.MD](Architecture.MD) - System architecture
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Developer onboarding

### **Pixel Detective**
- [Backend Architecture](backend/ARCHITECTURE.md)
- [Frontend Architecture](frontend/ARCHITECTURE.md)
- [Ingestion API](backend/ingestion_orchestration_fastapi_app/README.md)
- [ML Inference API](backend/ml_inference_fastapi_app/README.md)
- [GPU-UMAP Service](backend/gpu_umap_service/README.md)

### **Dev Graph**
- [Dev Graph Architecture](developer_graph/architecture.md)
- [Dev Graph Agents](developer_graph/AGENTS.md)
- [Route Documentation](developer_graph/routes/AGENTS.md)
- [Migration Plan](docs/DEV_GRAPH_MIGRATION_PLAN.md)

### **Cursor Rules** (`.cursor/rules/`)
- `projectrules.mdc` - Master rules
- `backend/backend-development-index.mdc` - Backend guide
- `frontend/frontend-development-index.mdc` - Frontend guide
- `sprint-lessons-learned.mdc` - Critical lessons
- `debugging.mdc` - Debugging guide

### **External Documentation**
- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/docs)
- [Neo4j Cypher](https://neo4j.com/docs/cypher-manual/)
- [Qdrant](https://qdrant.tech/documentation/)
- [Chakra UI](https://chakra-ui.com/docs)
- [DeckGL](https://deck.gl/docs)

---

## 🎓 **Learning Path for New AI Agents**

### **Week 1: Orientation**
- Day 1-2: Read README.md, Architecture.MD, this file
- Day 3-4: Explore codebase structure, run both applications
- Day 5: Make minor documentation improvements

### **Week 2: Pixel Detective**
- Day 1-2: Study backend architecture, run ingestion
- Day 3-4: Study frontend, implement UI enhancement
- Day 5: Fix a bug or add small feature

### **Week 3: Dev Graph**
- Day 1-2: Study Neo4j data model, run ingestion
- Day 3-4: Study timeline visualization, enhance UI
- Day 5: Add new graph query or improve linking

### **Week 4: Integration**
- Day 1-3: Work on cross-cutting feature
- Day 4-5: Performance optimization or testing

---

## ⚠️ **Critical Warnings**

### **Never Do These**

❌ **Don't**: Import `main.py` from routers (circular imports)  
✅ **Do**: Use dependency injection with `Depends()`

❌ **Don't**: Block event loop with synchronous operations  
✅ **Do**: Use `asyncio.to_thread()` for CPU-bound work

❌ **Don't**: Ignore GPU memory management  
✅ **Do**: Always call `torch.cuda.empty_cache()`

❌ **Don't**: Use manual `useEffect` for API calls  
✅ **Do**: Use React Query hooks

❌ **Don't**: Hardcode environment-specific values  
✅ **Do**: Use environment variables and config.py

❌ **Don't**: Skip error handling  
✅ **Do**: Handle all exceptions gracefully

❌ **Don't**: Create databases without indexes  
✅ **Do**: Define proper indexes and constraints

❌ **Don't**: Store secrets in code  
✅ **Do**: Use environment variables

### **Always Do These**

✅ **Read existing code first** - Understand patterns  
✅ **Follow conventions** - Match existing style  
✅ **Test your changes** - Automated tests required  
✅ **Update documentation** - Keep docs current  
✅ **Handle errors** - Graceful degradation  
✅ **Log appropriately** - Structured logging  
✅ **Profile performance** - No obvious bottlenecks  
✅ **Review security** - Validate inputs

---

## 📞 **Getting Help**

### **Where to Look**

1. **This file** (`AGENTS.md`) - General guidelines
2. **Service-specific AGENTS.md** - Detailed patterns
3. **Architecture docs** - System design
4. **Cursor rules** - Context-specific guidelines
5. **Code comments** - Implementation details

### **Debugging Resources**

- `.cursor/rules/debugging.mdc` - Debugging guide
- `.cursor/rules/quick-troubleshooting-index.mdc` - Quick fixes
- Service health endpoints - Real-time diagnostics
- FastAPI `/docs` - Interactive API testing

---

## 🎯 **Success Criteria**

An AI agent is successful when:

✅ **Code Quality**: Matches existing patterns and conventions  
✅ **Functionality**: Feature works as expected  
✅ **Testing**: Adequate test coverage  
✅ **Documentation**: Clear and complete  
✅ **Performance**: No regressions  
✅ **Security**: No vulnerabilities introduced  
✅ **Maintainability**: Easy for next agent to understand

---

**Last Updated**: Sprint 11 (September 2025)  
**Version**: 2.0 (Dual Platform)  
**Status**: Production Guidelines

**🚀 Built with AI | 🎨 Guided by Patterns | 💡 Evolving with Experience**

