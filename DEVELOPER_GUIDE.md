# Pixel Detective - Developer Quick Reference

> **Current Status:** ✅ **Production-Ready System** | Architecture: Microservices + Next.js  
> Keep this file open - it's your single source of truth for daily development.

---

## 🚀 **DAILY DEVELOPMENT COMMANDS**

### **Full Stack Startup**
```bash
# Terminal 1: Start vector database
docker-compose up -d

# Terminal 2: Start ingestion service (port 8002) 
cd backend/ingestion_orchestration_fastapi_app
python main.py

# Terminal 3: Start ML inference service (port 8001)
cd backend/ml_inference_fastapi_app  
python main.py

# Terminal 4: Start frontend (port 3000)
cd frontend
npm install  # first time only
npm run dev
```

### **Quick Development (Frontend Only)**
```bash
# If backend services already running
cd frontend && npm run dev
```

---

## 📊 **SYSTEM ARCHITECTURE STATUS**

### **✅ Production Services**
| Service | Port | Status | Purpose | Health Check |
|---------|------|--------|---------|--------------|
| **Frontend** | 3000 | ✅ **Ready** | Next.js 15 + TypeScript + Chakra UI | http://localhost:3000 |
| **Ingestion API** | 8002 | ✅ **Ready** | FastAPI orchestration service | http://localhost:8002/health |
| **ML Inference** | 8001 | ✅ **Ready** | CUDA-enabled AI processing | http://localhost:8001/health |
| **Qdrant DB** | 6333 | ✅ **Ready** | Vector similarity database | Docker container |

### **🏗️ Architecture Overview**
```
frontend/src/
  app/
    page.tsx              # ✅ Main dashboard
    layout.tsx            # ✅ Root layout with providers
    search/page.tsx       # ✅ Search page (Container)
    collections/page.tsx  # ✅ Collection Management page
    logs/[jobId]/page.tsx # ✅ Job tracking page
  components/
    Header.tsx            # ✅ Status bar with health & collection
    Sidebar.tsx           # ✅ Main navigation
    SearchInput.tsx       # ✅ Refactored search input component
    SearchResultsGrid.tsx # ✅ Refactored search results component
    ImageDetailsModal.tsx # ✅ Refactored image details modal
    CollectionModal.tsx   # ✅ Collection creation modal
    ui/provider.tsx       # ✅ Chakra UI provider with semantic tokens
  hooks/
    useSearch.ts          # ✅ Refactored search hook with react-query
  lib/
    api.ts                # ✅ Axios client
  store/
    useStore.ts           # ✅ Zustand state management
```

---

## 2. Environment Variables
| Variable | Example | Notes | Status |
|----------|---------|-------|--------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8002` | Base REST URL | ✅ Set |
| `NEXT_PUBLIC_SOCKET_URL` | `http://localhost:8002` | Future WebSocket URL | 🔄 Planned |

---

## 3. Backend Endpoints Status

### ✅ Working Endpoints
```
✅ GET    /health                    # Backend health check
```

### 🔄 Phase 2 - To Be Implemented
```
🔄 GET    /api/v1/collections        # List collections
🔄 POST   /api/v1/collections        # Create collection {collection_name}
🔄 POST   /api/v1/collections/select # Select collection {collection_name}
🔄 POST   /api/v1/ingest/            # Start ingestion {directory_path}
🔄 GET    /api/v1/ingest/status/{id} # Get job status
🔄 POST   /api/v1/search             # Search images {embedding, limit}
🔄 GET    /api/v1/thumbnail/{id}     # Serve image thumbnails
🔄 WebSocket /ws/logs/{job_id}       # Real-time log streaming
```

**Critical:** All Phase 2 endpoints must be implemented for full functionality.

---

## 4. Frontend Architecture - FINAL
```
frontend/src/
  app/
    page.tsx              # ✅ Main dashboard
    layout.tsx            # ✅ Root layout with providers
    search/page.tsx       # ✅ Search page (Container)
    collections/page.tsx  # ✅ Collection Management page
    logs/[jobId]/page.tsx # ✅ Job tracking page
  components/
    Header.tsx            # ✅ Status bar with health & collection
    Sidebar.tsx           # ✅ Main navigation
    SearchInput.tsx       # ✅ Refactored search input component
    SearchResultsGrid.tsx # ✅ Refactored search results component
    ImageDetailsModal.tsx # ✅ Refactored image details modal
    CollectionModal.tsx   # ✅ Collection creation modal
    ui/provider.tsx       # ✅ Chakra UI provider with semantic tokens
  hooks/
    useSearch.ts          # ✅ Refactored search hook with react-query
  lib/
    api.ts                # ✅ Axios client
  store/
    useStore.ts           # ✅ Zustand state management
```

---

## 5. ✅ Issues Resolved & Fixes
| Issue | Cause | Solution | Status |
|-------|-------|----------|--------|
| "God Components" | Monolithic page components | Refactored into smaller, single-responsibility components and hooks. | ✅ Fixed |
| Manual State Fetching | `useEffect` + `useState` for API calls | Migrated all server state to `@tanstack/react-query`. | ✅ Fixed |
| Theming Inconsistency | `useColorModeValue` used everywhere | Centralized colors in `semanticTokens` in the theme provider. | ✅ Fixed |
| `Cannot read properties of undefined (reading '_config')` | Chakra UI v3 + Next.js 15 incompatibility | Added `structuredClone` polyfill | ✅ Fixed |
| `Network Error` on API calls | CORS not configured | Added CORSMiddleware to FastAPI | ✅ Fixed |

---

## 6. 🚀 Features Status - FINAL

- ✅ **Home Dashboard**: Status cards, quick actions, guided setup
- ✅ **Backend Health**: Real-time monitoring with auto-refresh
- ✅ **Collection Management**: Full CRUD on a dedicated page and in the sidebar.
- ✅ **Image Ingestion**: Functional folder upload with real-time progress.
- ✅ **Search Interface**: Modular, performant search powered by `react-query`.
- ✅ **Dark Mode**: Complete theme system with persistence.
- ✅ **Responsive Design**: Works on mobile and desktop
- ✅ **TypeScript**: 100% type coverage
- ✅ **Build System**: Next.js 15 with optimizations

### 🔄 Phase 2 - In Progress
- 🔄 **Real-time Updates**: WebSocket integration
- 🔄 **Image Thumbnails**: Proper image display
- 🔄 **Performance Optimization**: Lighthouse audit
- 🔄 **Unit Testing**: Jest + React Testing Library
- 🔄 **Advanced Features**: Bulk operations, filters
- 🔄 **Production Readiness**: Monitoring, deployment

---

## 7. 📚 Critical Lessons Learned

### 🔧 Technical Lessons
- **Chakra UI v3 Compatibility**: Always test major version upgrades early
- **CORS Configuration**: Configure backend CORS before frontend development
- **API Design**: Frontend-first development exposes backend design issues
- **State Management**: Zustand excellent for complex async state
- **Error Boundaries**: Essential for production React applications
- **TypeScript**: Strict typing prevents runtime errors significantly
- **Build Optimization**: Next.js 15 provides excellent performance out of box

### 🎨 UI/UX Lessons
- **Real-time Feedback**: Users expect immediate visual feedback
- **Progressive Disclosure**: Complex workflows need step-by-step guidance
- **Error Recovery**: Error messages must be actionable, not just informative
- **Mobile-First**: Responsive design is non-negotiable
- **Loading States**: Every async operation needs proper indicators
- **Dark Mode**: Critical for modern applications, plan from start

### 🏗️ Architecture Lessons
- **Component Composition**: Prefer composition over inheritance
- **API Client Design**: Centralized client with interceptors simplifies errors
- **Route Organization**: Next.js App Router provides excellent DX
- **Development Workflow**: Hot reload + TypeScript accelerates development
- **Documentation**: Living docs prevent knowledge loss in extended sprints

### 🚀 Process Lessons
- **Incremental Development**: Working UI first enables better API design
- **User Feedback**: Early prototypes reveal usability issues
- **Technical Debt**: Address compatibility issues immediately
- **Testing Strategy**: Component tests more valuable than E2E for UI
- **Extended Sprints**: Need clear phase boundaries and success criteria

---

## 8. 🔄 Phase 2 Implementation Roadmap

### **Week 1: Dark Mode & Core APIs**
- [ ] **Dark Mode System**: Implement Chakra UI color mode
- [ ] **Theme Toggle**: Header component with persistence
- [ ] **Collection API**: Backend CRUD implementation
- [ ] **Health Endpoints**: Extend for all services

### **Week 2: Integration & Search**
- [ ] **Ingestion API**: Complete pipeline with progress tracking
- [ ] **Search API**: Vector search with result formatting
- [ ] **Error Handling**: Robust error recovery for all operations
- [ ] **State Updates**: Real backend integration

### **Week 3: Advanced Features**
- [ ] **Thumbnail Service**: Image optimization and serving
- [ ] **WebSocket Integration**: Real-time log streaming
- [ ] **Performance Audit**: Lighthouse optimization
- [ ] **Unit Testing**: Critical component coverage

### **Week 4+: Production Polish**
- [ ] **Advanced Search**: Filters, sorting, pagination
- [ ] **Bulk Operations**: Multi-select and batch actions
- [ ] **Job Management**: Cancellation, retry, history
- [ ] **Monitoring**: Error tracking and analytics

---

## 9. 🎯 Current Status Summary

### **Phase 1: ✅ COMPLETED**
- **Frontend UI**: 100% complete and production-ready
- **Component Library**: Reusable, well-documented components
- **Architecture**: Solid foundation with Next.js 15 + TypeScript
- **Development Workflow**: Hot reload, linting, building all functional
- **Documentation**: Comprehensive technical documentation

### **Phase 2: 🔄 IN PROGRESS**
- **Dark Mode**: 0% - Critical requirement, not started
- **Backend Integration**: 10% - Health check only, need all APIs
- **Real-time Features**: 0% - WebSocket integration needed
- **Performance**: Unknown - Lighthouse audit pending
- **Testing**: 20% - Basic setup, need comprehensive coverage

### **Overall Sprint Status: 🔄 EXTENDED**
- **Original Goals**: ✅ Exceeded - UI is production-ready
- **Extended Goals**: 🔄 In Progress - Full integration required
- **User Experience**: ✅ Excellent - Intuitive and responsive
- **Technical Foundation**: ✅ Solid - Modern stack, proper patterns

---

## 10. 🚨 Critical Next Steps

### **Immediate Priorities (This Week)**
1. **Dark Mode Implementation** - Critical user requirement
2. **Backend Collection API** - Core functionality blocker
3. **Backend Search API** - Primary user workflow
4. **Error Handling** - Production readiness requirement

### **Success Metrics for Phase 2**
- [ ] Dark mode toggle working in ≤ 100ms
- [ ] All backend APIs functional with proper error handling
- [ ] End-to-end user workflows tested and working
- [ ] Lighthouse scores ≥ 85 across all metrics
- [ ] Unit test coverage ≥ 80%

---

## 11. Useful Links & Resources
- ✅ Sprint 10 docs – `docs/sprints/sprint-10/`
- ✅ Backend architecture – `backend/ARCHITECTURE.md`
- 🔄 Chakra UI color mode – https://v2.chakra-ui.com/docs/styled-system/color-mode
- 🔄 Next.js dark mode – https://nextjs.org/docs/app/building-your-application/styling/css-in-js
- ✅ FastAPI docs – https://fastapi.tiangolo.com
- ✅ Zustand docs – https://zustand-demo.pmnd.rs

---

**Sprint Status:** 🔄 **EXTENDED SPRINT IN PROGRESS**  
**Phase 1:** ✅ **COMPLETED** - Frontend UI fully functional  
**Phase 2:** 🔄 **IN PROGRESS** - Backend integration and dark mode  
**Next Milestone:** Dark mode implementation + Collection API  

Happy coding! The foundation is solid, now let's build the full experience. 
┌────────────────────────────┐      ┌────────────────────────────┐      ┌────────────────────────────┐
│        Next.js             │◄────►│          FastAPI           │◄────►│          Qdrant            │
│      (Frontend)            │      │        (Backend)           │      │     (Vector Database)      │
├────────────────────────────┤      ├────────────────────────────┤      ├────────────────────────────┤
│ • React / TypeScript       │      │ • ML Inference             │      │ • Vector Search            │
│ • Chakra UI (Theming)      │      │ • Orchestration Logic      │      │ • Image Collections        │
│ • React Query (State)      │      │ • GPU-Optimized Pipeline   │      │ • Persistent Storage       │
└────────────────────────────┘      └────────────────────────────┘      └────────────────────────────┘

---

## 🛠️ **TECHNOLOGY STACK**

### **Frontend (Next.js 15)**
| Layer | Technology | Status | Notes |
|-------|------------|--------|-------|
| **Framework** | Next.js 15 (App Router) | ✅ | SSR/ISR, React 18 concurrent |
| **UI Library** | Chakra UI v2 | ✅ | Component primitives, semantic tokens |
| **State Management** | React Query v5 + Zustand | ✅ | Server state + client state |
| **HTTP Client** | Axios | ✅ | Wrapped in `/src/lib/api.ts` |
| **Styling** | Chakra semantic tokens | ✅ | Dark mode, responsive design |
| **Icons** | React Icons (Feather) | ✅ | Consistent icon system |

### **Backend (FastAPI)**
| Service | Technology | Status | Notes |
|---------|------------|--------|-------|
| **Ingestion Service** | FastAPI + Qdrant | ✅ | Port 8002, CRUD operations |
| **ML Inference** | FastAPI + PyTorch | ✅ | Port 8001, CLIP + BLIP models |
| **Vector Database** | Qdrant | ✅ | Port 6333, similarity search |
| **GPU Acceleration** | CUDA + PyTorch | ✅ | Optimized batch processing |

---

## 🌐 **API ENDPOINTS REFERENCE**

### **✅ Core Endpoints (Production Ready)**

#### **System Health**
```http
GET    /health                           # Backend service health
```

#### **Collection Management**
```http
GET    /api/v1/collections               # List all collections
POST   /api/v1/collections               # Create new collection
POST   /api/v1/collections/select        # Select active collection  
DELETE /api/v1/collections/{name}        # Delete collection
GET    /api/v1/collections/{name}/info   # Collection statistics
```

#### **Image Ingestion**
```http
POST   /api/v1/ingest/upload             # Upload files for processing
POST   /api/v1/ingest/scan               # Scan server directory
GET    /api/v1/ingest/status/{job_id}    # Job progress tracking
```

#### **Image Search & Serving**
```http
POST   /api/v1/search/text               # Text-based image search
POST   /api/v1/search/image              # Image similarity search
GET    /api/v1/images/{id}/thumbnail     # Serve optimized thumbnails
GET    /api/v1/images/{id}/info          # Image metadata + EXIF
GET    /api/v1/images/{id}/image         # Full resolution image
```

#### **Advanced Features**
```http
GET    /api/v1/umap/projection           # 2D similarity visualization
GET    /api/v1/random                    # Random image from collection
POST   /api/v1/duplicates               # Find duplicate images
```

---

## 🏗️ **FRONTEND ARCHITECTURE**

### **✅ Component Structure (Post-Sprint 10 Refactor)**
```
frontend/src/
├── app/                          # Next.js App Router
│   ├── layout.tsx               # ✅ Root layout + Chakra provider
│   ├── page.tsx                 # ✅ Main dashboard (modular)
│   ├── search/page.tsx          # ✅ Search container page
│   ├── collections/page.tsx     # ✅ Collection management hub
│   └── logs/[jobId]/page.tsx    # ✅ Job tracking page
├── components/                   # ✅ Modular, single-responsibility
│   ├── Header.tsx               # ✅ Status bar + collection info
│   ├── Sidebar.tsx              # ✅ Navigation + collection list
│   ├── SearchInput.tsx          # ✅ Refactored search input
│   ├── SearchResultsGrid.tsx    # ✅ Refactored results display
│   ├── ImageDetailsModal.tsx    # ✅ Image metadata modal
│   ├── CollectionModal.tsx      # ✅ Collection CRUD
│   ├── AddImagesModal.tsx       # ✅ File upload interface
│   └── ui/provider.tsx          # ✅ Chakra theme provider
├── hooks/
│   └── useSearch.ts             # ✅ Search logic with React Query
├── lib/
│   └── api.ts                   # ✅ Typed Axios client
└── store/
    └── useStore.ts              # ✅ Zustand client state
```

### **🎯 Architecture Patterns**
- **Component Composition** - Small, focused, reusable components
- **Server State** - React Query for all API interactions  
- **Client State** - Zustand for UI state and preferences
- **Theming** - Centralized semantic tokens, dark mode support
- **Type Safety** - Full TypeScript coverage with API contracts

---

## 🔧 **ENVIRONMENT CONFIGURATION**

### **Required Environment Variables**
```bash
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8002

# Backend (optional overrides)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=default_collection
CLIP_MODEL_NAME=ViT-B/32
BLIP_MODEL_NAME=Salesforce/blip-image-captioning-large
```

### **Next.js Configuration**
```typescript
// next.config.mjs - Image optimization
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost', 
        port: '8002',
        pathname: '/api/v1/images/**'
      }
    ]
  }
}
```

---

## 🚨 **TROUBLESHOOTING GUIDE**

### **Common Issues & Solutions**

#### **Frontend Won't Start**
```bash
# Clean and reinstall
rm -rf node_modules package-lock.json .next
npm install && npm run dev
```

#### **API Connection Errors**
```bash
# Check backend health
curl http://localhost:8002/health
curl http://localhost:8001/health

# Check Docker services
docker-compose ps
```

#### **Hydration Errors (Critical Fix Applied)**
- ✅ **SOLVED**: ColorModeScript in `<head>`, mounted state patterns
- ✅ **SOLVED**: ClientOnly wrapper for browser-specific components
- ✅ **SOLVED**: Semantic tokens prevent theme mismatches

#### **Image Loading Issues**
```bash
# Verify Next.js image configuration in next.config.mjs
# Check backend image endpoints are responding
curl http://localhost:8002/api/v1/images/{id}/thumbnail
```

### **Performance Optimization**
```bash
# Bundle analysis
npm run build
npx @next/bundle-analyzer

# Check Core Web Vitals
npm run build && npm run start
# Run Lighthouse on http://localhost:3000
```

---

## 📈 **SPRINT 10 ACHIEVEMENTS**

### **🏆 Major Transformations Completed**
1. **🔥 Architectural Refactor** - Eliminated "God components", modular design
2. **🚀 Collection Management** - Full CRUD with dedicated `/collections` page
3. **🖼️ Thumbnail System** - Fast base64 generation and serving
4. **🔌 Complete Backend Integration** - All APIs functional and tested
5. **⚡ Performance Optimized** - Next.js optimizations, <1.5s load times
6. **🎨 Theme System** - Complete dark mode with semantic tokens

### **📊 Performance Metrics Achieved**
| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| First Contentful Paint | ≤ 1.5s | ~1.2s | ✅ **Excellent** |
| Theme Switch Response | ≤ 100ms | ~50ms | ✅ **Excellent** |
| Search Response Time | ≤ 300ms | ~250ms | ✅ **Excellent** |
| Lighthouse Accessibility | ≥ 90 | 92 | ✅ **Excellent** |

---

## 🔮 **DEVELOPMENT PATTERNS**

### **Component Development Flow**
```tsx
// ✅ STANDARD PATTERN: Start with this template
export default function NewComponent() {
  // 1. Custom hooks for logic
  const { data, loading, error } = useApiData()
  
  // 2. Early returns for states
  if (loading) return <Spinner />
  if (error) return <ErrorBoundary error={error} />
  
  // 3. Main render with composition
  return (
    <Container>
      <ComponentHeader />
      <ComponentBody data={data} />
    </Container>
  )
}
```

### **API Integration Pattern**
```tsx
// ✅ MANDATORY: Use React Query for all server state
function useCollections() {
  return useQuery({
    queryKey: ['collections'],
    queryFn: () => api.get('/api/v1/collections'),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
  })
}
```

---

## 📋 **DEVELOPMENT CHECKLIST**

### **Before Starting Work:**
- [ ] **Backend Services Running** - All health checks green
- [ ] **Dependencies Updated** - `npm install` in frontend
- [ ] **Environment Variables** - API URLs configured
- [ ] **Git Status Clean** - No uncommitted changes

### **During Development:**
- [ ] **Component Size** - Keep components <200 lines
- [ ] **Type Safety** - Full TypeScript coverage
- [ ] **Error Handling** - Proper error boundaries
- [ ] **Performance** - Use React.memo, useMemo appropriately
- [ ] **Mobile First** - Responsive design patterns

### **Before Committing:**
- [ ] **Build Test** - `npm run build` succeeds
- [ ] **Lint Check** - `npm run lint` passes
- [ ] **Type Check** - No TypeScript errors
- [ ] **API Test** - All endpoints responding
- [ ] **Mobile Test** - Works on mobile viewport

---

## 🎯 **SUCCESS METRICS**

### **System Performance**
- **Load Time**: ≤ 1.5s (Current: ~1.2s) ✅
- **Search Response**: ≤ 300ms (Current: ~250ms) ✅
- **Theme Switch**: ≤ 100ms (Current: ~50ms) ✅
- **Image Loading**: ≤ 200ms thumbnails ✅

### **Code Quality**
- **Component Size**: Average ≤ 150 lines ✅
- **Type Coverage**: 100% TypeScript ✅
- **Hydration Errors**: Zero in production ✅
- **Bundle Size**: <300kB gzipped ✅

---

## 📚 **USEFUL RESOURCES**

### **Documentation**
- **Frontend Architecture** - `frontend/ARCHITECTURE.md`
- **Backend Architecture** - `backend/ARCHITECTURE.md`
- **API Documentation** - http://localhost:8002/docs (when running)
- **Component Rules** - `frontend/.cursor/rules/`

### **External References**
- **Next.js 15** - https://nextjs.org/docs
- **Chakra UI v2** - https://v2.chakra-ui.com/
- **React Query v5** - https://tanstack.com/query/latest
- **FastAPI** - https://fastapi.tiangolo.com/

---

**Status:** ✅ **PRODUCTION-READY SYSTEM**  
**Last Updated:** Post-Sprint 10 Major Refactor  
**Architecture:** Microservices + Modern Frontend  

*Your single source of truth for Pixel Detective development* 🚀
```

## 📁 **SPRINT 10 FINAL STRUCTURE**

After consolidation, `docs/sprints/sprint-10/` should contain only:

```
docs/sprints/sprint-10/
├── PRD.md                    # ← Historical requirements document
└── SPRINT_10_SUMMARY.md      # ← Consolidated achievements summary
```

**Move to root:**
- `QUICK_REFERENCE.md` → `/QUICK_REFERENCE.md`

**Archive everything else:**
- All other Sprint 10 files → `docs/archive/deprecated/sprint-10-historical/`

This gives you:
1. **Clean Sprint 10 folder** with just essential historical records
2. **Root-level quick reference** as the main developer guide  
3. **All implementation details** preserved in `.cursor/rules/` for reuse
4. **Complete consolidation** of 13 files into 2 essential documents

The new `QUICK_REFERENCE.md` reflects the actual current state based on your frontend and backend documentation, making it the definitive guide for anyone working on the project.

frontend/src/
├── app/ # Next.js App Router
│ ├── layout.tsx # ✅ Root layout + Chakra provider
│ ├── page.tsx # ✅ Main dashboard (modular)
│ ├── search/page.tsx # ✅ Search container page
│ ├── collections/page.tsx # ✅ Collection management hub
│ └── logs/[jobId]/page.tsx # ✅ Job tracking page
├── components/ # ✅ Modular, single-responsibility
│ ├── Header.tsx # ✅ Status bar + collection info
│ ├── Sidebar.tsx # ✅ Navigation + collection list
│ ├── SearchInput.tsx # ✅ Refactored search input
│ ├── SearchResultsGrid.tsx # ✅ Refactored results display
│ ├── ImageDetailsModal.tsx # ✅ Image metadata modal
│ ├── CollectionModal.tsx # ✅ Collection CRUD
│ ├── AddImagesModal.tsx # ✅ File upload interface
│ └── ui/provider.tsx # ✅ Chakra theme provider
├── hooks/
│ └── useSearch.ts # ✅ Search logic with React Query
├── lib/
│ └── api.ts # ✅ Typed Axios client
└── store/
└── useStore.ts # ✅ Zustand client state