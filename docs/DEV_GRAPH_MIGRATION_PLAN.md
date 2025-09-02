# Dev Graph Migration - Detailed Implementation Plan

**Status**: Ready for Execution  
**Last Updated**: 2025-01-27  
**Priority**: High - Performance isolation and standalone deployment

---

## Executive Summary

The Dev Graph migration is **ready for immediate execution**. The current codebase contains a complete, production-ready implementation with:

- ✅ **Complete FastAPI service** with comprehensive Git integration
- ✅ **Full Neo4j schema** with temporal relationships  
- ✅ **Comprehensive frontend** with Sigma.js visualization
- ✅ **Docker containerization** with proper networking
- ✅ **Git history service** with commit parsing and file tracking
- ✅ **Sprint mapping** and temporal analytics

Update (2025‑09‑02): Doc‑first graph coverage expanded
- ✅ Chunk nodes extracted from Markdown (H1/H2/H3) with stable IDs
- ✅ Sprint→Document, Document→Chunk, and Chunk→Requirement (MENTIONS) edges
- ✅ Constraint added for unique `Chunk.id`
- ⚠️ Note: Rebuild `dev_graph_api` image after changes to `developer_graph/*` or bind‑mount the folder for live development

**Key Insight**: This is not a development project - it's a **deployment and extraction project**. The implementation is complete and ready for standalone deployment.

---

## Phase 1: Immediate Standalone Deployment (Ready Now)

### Step 1.1: Test Current Docker Setup
```bash
# Navigate to project root
cd /c/Users/aitor/OneDrive/Escritorio/Vibe\ Coding

# Start only Dev Graph services
docker compose up -d neo4j dev_graph_api

# Verify services are running
docker compose ps

# Test API endpoints
curl http://localhost:8080/api/v1/dev-graph/nodes/count
curl http://localhost:8080/api/v1/dev-graph/commits?limit=10
```

If you changed code under `developer_graph/`, rebuild the API image first:
```bash
docker compose build dev_graph_api && docker compose up -d dev_graph_api
```

**Expected Results**:
- Neo4j accessible at `http://localhost:7474`
- API accessible at `http://localhost:8080/docs`
- Commits endpoint returns recent commits
- Nodes endpoint returns graph data

### Step 1.2: Ingest Initial Data
```bash
# Ingest recent commits into Neo4j
curl -X POST "http://localhost:8080/api/v1/dev-graph/ingest/recent?limit=100"

# Verify data ingestion
curl "http://localhost:8080/api/v1/dev-graph/nodes/count"
curl "http://localhost:8080/api/v1/dev-graph/relations/count"
```

**Expected Results**:
- 100+ commits ingested
- 1000+ nodes created (commits, files, requirements)
- 2000+ relationships created (TOUCHED, IMPLEMENTS, etc.)

Optional: Run enhanced doc ingestion (adds sprints, documents, chunks, mentions)
```bash
# From the host
docker exec -it $(docker compose ps -q dev_graph_api) \
  python -m developer_graph.enhanced_ingest

# Verify new node/edge types
curl "http://localhost:8080/api/v1/dev-graph/nodes?node_type=Document"
curl "http://localhost:8080/api/v1/dev-graph/nodes?node_type=Chunk"
curl "http://localhost:8080/api/v1/dev-graph/relations?rel_type=CONTAINS_DOC"
curl "http://localhost:8080/api/v1/dev-graph/relations?rel_type=CONTAINS_CHUNK"
curl "http://localhost:8080/api/v1/dev-graph/relations?rel_type=MENTIONS"
```

### Step 1.3: Test Frontend Integration
```bash
# Start main frontend (if not already running)
cd frontend
npm run dev

# Access Dev Graph at http://localhost:3000/dev-graph
# Verify all tabs work: Timeline, Sprint, Analytics
# Test graph visualization and node interactions
```

**Expected Results**:
- Frontend loads without errors
- Timeline shows commit history
- Sprint view shows sprint data
- Graph visualization renders nodes and edges
- Node details drawer works

---

## Phase 2: Standalone UI Extraction (Next Priority)

### Step 2.1: Create Standalone Next.js App
```bash
# Create new standalone app
mkdir -p tools/dev-graph-ui
cd tools/dev-graph-ui

# Initialize Next.js project
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

# Install required dependencies
npm install @chakra-ui/react @emotion/react @emotion/styled framer-motion
npm install @tanstack/react-query
npm install graphology graphology-layout-forceatlas2 graphology-layout-force
npm install sigma
```

### Step 2.2: Copy Frontend Components
```bash
# Copy Dev Graph components
cp -r ../../frontend/src/app/dev-graph/* src/app/dev-graph/

# Update API URL configuration
# In src/app/dev-graph/page.tsx, update:
# const DEV_GRAPH_API_URL = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';

# Ensure CORS in API allows the UI origin (e.g., http://localhost:3001)
# Optionally set env var CORS_ORIGINS in dev_graph_api service
```

### Step 2.3: Create Standalone Layout
```bash
# Create minimal layout without main app dependencies
# Update src/app/layout.tsx to remove main app header/footer
# Create standalone navigation for Dev Graph
```

### Step 2.4: Test Standalone UI
```bash
# Start standalone UI
npm run dev

# Access at http://localhost:3001
# Verify all functionality works independently
```

---

## Phase 3: Remove from Main App (Cleanup)

### Step 3.1: Remove Dev Graph from Main Frontend
```bash
# Remove Dev Graph route from main app
rm -rf frontend/src/app/dev-graph/

# Update main app navigation to link to standalone UI
# Add link to http://localhost:3001 in main app header
```

### Step 3.2: Update Docker Compose
```bash
# Add standalone UI service to docker-compose.yml
# Create separate network for Dev Graph services
# Update CORS configuration for standalone UI
```

---

## Phase 4: Enhanced Features (Future)

### Step 4.1: Remote Repository Support
```bash
# Add entrypoint.sh to API container
# Support GIT_REMOTE_URL and GIT_BRANCH environment variables
# Implement automatic repository cloning on startup
```

### Step 4.2: Performance Optimization
```bash
# Add Redis caching for frequently accessed data
# Implement query result caching
# Add pagination for large result sets
```

### Step 4.3: Export/Import Capabilities
```bash
# Add graph export to JSON
# Add graph import from JSON
# Add snapshot creation and restoration
```

---

## Immediate Action Items

### Today (Ready to Execute)
1. **Test Current Implementation**: Run Phase 1 steps to verify everything works
2. **Document API Usage**: Create API documentation with examples
3. **Performance Testing**: Test with full repository history
4. **Run Enhanced Ingest**: Execute `developer_graph.enhanced_ingest` to create Chunk graph
5. **Create Standalone UI**: Begin Phase 2 UI extraction

### This Week
1. **Complete UI Extraction**: Finish standalone Next.js app
2. **Remove from Main App**: Clean up main frontend
3. **Update Documentation**: Create user guides and deployment docs
4. **Performance Optimization**: Add caching and query optimization

### Next Week
1. **Remote Repository Support**: Add Git cloning capabilities
2. **Enhanced Features**: Add export/import and advanced analytics
3. **Production Deployment**: Deploy to production environment
4. **Monitoring**: Add logging and monitoring capabilities

---

## Success Criteria

### Phase 1 Success
- ✅ Docker services start without errors
- ✅ API endpoints return expected data
- ✅ Frontend displays graph visualization
- ✅ Node interactions work correctly
- ✅ Doc-first graph present (Sprint→Document→Chunk, Chunk→Requirement)

### Phase 2 Success
- ✅ Standalone UI works independently
- ✅ All features function without main app
- ✅ Performance is acceptable
- ✅ User experience is maintained

### Phase 3 Success
- ✅ Main app no longer includes Dev Graph
- ✅ Standalone UI is accessible
- ✅ No breaking changes to main app
- ✅ Clean separation achieved

---

## Risk Mitigation

### Technical Risks
- **Docker Issues**: Test on clean environment, document requirements
- **API Compatibility**: Version APIs, maintain backward compatibility
- **Performance**: Monitor resource usage, implement limits

### Operational Risks
- **Data Loss**: Backup Neo4j data before migration
- **Service Dependencies**: Gradual migration, feature flags
- **User Experience**: Maintain functionality during transition

---

## Conclusion

The Dev Graph migration is **ready for immediate execution**. The implementation is complete and production-ready. The main work is deployment, extraction, and cleanup - not development.

**Next Action**: Execute Phase 1 steps to verify current implementation works correctly, then proceed with UI extraction and standalone deployment.
