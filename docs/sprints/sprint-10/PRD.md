# Sprint 10 Extended – Product Requirements Document (PRD)

> **Codename:** _Critical UI Refactor – Full Backend Integration v1.0_
> **Duration:** Extended Sprint (originally 2 weeks, now ongoing until completion)  
> **Phase 1:** ✅ Frontend UI Complete  
> **Phase 2:** 🔄 Backend Integration + Dark Mode  
> **Prepared for:** Development Team  
> **Related Docs:** [`technical-implementation-plan.md`](./technical-implementation-plan.md), [`README.md`](./README.md)

---

## 1. Executive Summary
Sprint 10 has been **extended beyond the original scope** to deliver a fully functional React/Next.js interface with complete backend integration. The original Phase 1 successfully delivered the frontend UI, but the sprint continues until all backend APIs are implemented and dark mode is fully functional.

**Phase 1 Completed:**
* ✅ System health display  
* ✅ Collection management UI (list / create / select)  
* ✅ Folder ingestion UI with live progress & logs  
* ✅ Basic vector search & result display UI  

**Phase 2 Extended Scope:**
* 🔄 **Full Backend API Integration** - All endpoints functional
* 🔄 **Dark Mode Implementation** - Complete theme system
* 🔄 **Advanced Features** - WebSocket, thumbnails, bulk operations
* 🔄 **Production Readiness** - Performance, testing, monitoring

This extended sprint ensures the application is fully operational and production-ready, not just a UI prototype.

---

## 2. Goals & Non-Goals

### 2.1 Phase 1 Goals – ✅ COMPLETED
1. ✅ **Operational UI** that a non-technical user can navigate end-to-end
2. ✅ **Shared frontend architecture** – routing, state, theming, data-fetch, linting, CI
3. ✅ **Live feedback framework** – job progress & logs UI components
4. ✅ **Documentation & CI** – sprint docs complete; GitHub Action builds passing

### 2.2 Phase 2 Goals – 🔄 IN PROGRESS
1. **Full Backend Integration** – All APIs implemented and functional
2. **Dark Mode Support** – Complete theme system with user preferences
3. **Production Features** – WebSocket, thumbnails, error recovery
4. **Performance Optimization** – Lighthouse audit ≥ 85 across all metrics
5. **Testing Coverage** – Unit tests for critical components

### 2.3 Still Out of Scope (Future Sprints)
* Latent Space visualisation, AI Guessing Game, Duplicate Detection UI  
* Desktop/Electron packaging & native folder picker
* Advanced analytics and monitoring dashboards
* Multi-user authentication and authorization

---

## 3. User Stories & Acceptance Criteria - Extended

### Phase 1 Stories - ✅ COMPLETED
| ID | User Story | Acceptance Criteria | Status |
|----|------------|--------------------|---------|
| FR-10-01 | As a user I open the web app and instantly see if backend services are healthy | Banner shows ✅ when both services return 200. Error banner if not. | ✅ Complete |
| FR-10-02 | I can view, create, and select collections (UI) | Modal shows collection list, create form, selection state | ✅ Complete |
| FR-10-03 | I can ingest images from a local folder and watch progress (UI) | Path input, job tracking page with progress indicators | ✅ Complete |
| FR-10-04 | I can search my collection with a text prompt (UI) | Search form with results grid layout | ✅ Complete |

### Phase 2 Stories - 🔄 IN PROGRESS
| ID | User Story | Acceptance Criteria | Priority | Status |
|----|------------|--------------------|----------|---------|
| FR-10-05 | I can toggle between light and dark mode | Theme toggle in header, preference persisted, all components support both modes | High | 🔄 Not started |
| FR-10-06 | I can actually create and manage collections | `GET /api/v1/collections`, `POST /api/v1/collections`, `POST /api/v1/collections/select` all functional | High | 🔄 Backend needed |
| FR-10-07 | I can actually ingest images and see real progress | `POST /api/v1/ingest/` returns job_id, `GET /api/v1/ingest/status/{id}` shows real progress | High | 🔄 Backend needed |
| FR-10-08 | I can actually search and see real results | `POST /api/v1/search` returns actual image results with thumbnails | High | 🔄 Backend needed |
| FR-10-09 | I can see image thumbnails in search results | `GET /api/v1/thumbnail/{id}` serves optimized image thumbnails | Medium | 🔄 Backend needed |
| FR-10-10 | I get real-time log updates during ingestion | WebSocket connection streams live logs instead of HTTP polling | Medium | 🔄 Backend needed |

### Non-Functional Requirements - Extended
| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-10-01 | App loads quickly | First Contentful Paint ≤ 1.5s | ✅ ~800ms |
| NFR-10-02 | Dark mode toggle is instant | Theme switch ≤ 100ms | 🔄 Not implemented |
| NFR-10-03 | Search response time | End-to-end search ≤ 300ms | 🔄 Backend needed |
| NFR-10-04 | Ingestion throughput | 25 images ≤ 120s | 🔄 Backend needed |
| NFR-10-05 | Code quality & CI | ESLint passes, tests ≥ 90% green | ✅ Maintained |
| NFR-10-06 | Accessibility | Lighthouse a11y ≥ 90 | 🔄 Pending audit |

---

## 4. Functional Requirements Matrix - Extended

### ✅ Phase 1 - UI Complete
1. **Health Banner** - `GET /health` endpoints working
2. **Collection Modal UI** - Complete interface for collection management
3. **Add Images Modal UI** - Complete interface for ingestion workflow
4. **Logs Page UI** - Complete interface for job tracking
5. **Search Page UI** - Complete interface for search workflow

### 🔄 Phase 2 - Backend Integration Required
1. **Dark Mode System**
   * Theme provider with light/dark modes
   * Header toggle component
   * localStorage persistence
   * System preference detection

2. **Collection API Integration**
   * `GET /api/v1/collections` - List all collections
   * `POST /api/v1/collections` - Create new collection
   * `POST /api/v1/collections/select` - Select active collection
   * Error handling and user feedback

3. **Ingestion API Integration**
   * `POST /api/v1/ingest/` - Start ingestion job
   * `GET /api/v1/ingest/status/{id}` - Get job status and logs
   * Real-time progress updates
   * Job completion notifications

4. **Search API Integration**
   * `POST /api/v1/search` - Execute vector search
   * `GET /api/v1/thumbnail/{id}` - Serve image thumbnails
   * Result formatting and display
   * Search performance optimization

5. **WebSocket Integration**
   * Real-time log streaming
   * Connection management
   * Fallback to HTTP polling

---

## 5. Non-Functional Requirements - Extended

### Performance Targets
* **Frontend Performance:** FCP ≤ 1.5s, LCP ≤ 2.5s, CLS ≤ 0.1
* **API Response Times:** Health ≤ 50ms, Search ≤ 300ms, Collections ≤ 100ms
* **Theme Toggle:** Dark/light mode switch ≤ 100ms
* **Real-time Updates:** WebSocket latency ≤ 50ms

### Accessibility & UX
* **Lighthouse Accessibility:** ≥ 90 score
* **Color Contrast:** WCAG AA compliance in both light and dark modes
* **Keyboard Navigation:** Full keyboard accessibility
* **Screen Reader:** Proper ARIA labels and semantic HTML

### Security & Reliability
* **CORS Configuration:** Proper origin restrictions
* **Error Handling:** Graceful degradation for all failure modes
* **Data Validation:** Input sanitization and validation
* **Connection Resilience:** Automatic reconnection for WebSocket

### Developer Experience
* **Hot Reload:** ≤ 1s for development changes
* **Build Time:** ≤ 30s for production build
* **Type Safety:** 100% TypeScript coverage
* **Code Quality:** ESLint + Prettier enforcement

---

## 6. Metrics & KPIs - Extended

### Phase 1 Metrics - ✅ ACHIEVED
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Build success rate | 100% | 100% | ✅ |
| Frontend load time | ≤ 2s | ~800ms | ✅ |
| Component coverage | 100% | 100% | ✅ |
| TypeScript coverage | 100% | 100% | ✅ |

### Phase 2 Metrics - 🔄 TARGETS
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| End-to-end collection workflow | ≤ 30s | N/A | 🔄 Backend needed |
| End-to-end search workflow | ≤ 10s | N/A | 🔄 Backend needed |
| End-to-end ingestion demo (25 images) | ≤ 120s | N/A | 🔄 Backend needed |
| Dark mode toggle | ≤ 100ms | N/A | 🔄 Not implemented |
| Lighthouse Performance | ≥ 85 | TBD | 🔄 Pending audit |
| Lighthouse Accessibility | ≥ 90 | TBD | 🔄 Pending audit |

---

## 7. Dependencies - Extended

### Infrastructure Dependencies
* **Backend Services:** FastAPI ingestion service (port 8002)
* **Database:** Qdrant vector database (port 6333)
* **Development:** Node ≥ 18, npm ≥ 9
* **Build:** Next.js 15, TypeScript 5+

### API Dependencies - 🔄 TO BE IMPLEMENTED
* **Collection Endpoints:** Full CRUD API implementation
* **Ingestion Endpoints:** Job management and progress tracking
* **Search Endpoints:** Vector search with result formatting
* **Thumbnail Service:** Image optimization and serving
* **WebSocket Service:** Real-time log streaming

### External Dependencies
* **Chakra UI v2:** Theme system and component library
* **Zustand:** State management
* **Axios:** HTTP client with interceptors
* **Socket.IO:** WebSocket client (when backend ready)

---

## 8. Risk Assessment - Extended

### High Risk Items
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Backend API delays | Blocks Phase 2 completion | High | Implement mock APIs for development |
| Dark mode complexity | UI inconsistencies | Medium | Use Chakra UI's built-in color mode |
| WebSocket implementation | Real-time features delayed | Medium | HTTP polling fallback working |
| Performance degradation | Poor user experience | Low | Regular Lighthouse audits |

### Technical Risks
* **State Management Complexity:** Multiple async operations and real-time updates
* **Error Handling:** Robust error recovery for all failure scenarios
* **Browser Compatibility:** Ensure compatibility across modern browsers
* **Memory Leaks:** Proper cleanup of WebSocket connections and timers

---

## 9. Success Criteria - Extended Sprint

### Phase 1 Success Criteria - ✅ ACHIEVED
1. ✅ **Operational UI:** Non-technical users can navigate all interfaces
2. ✅ **Architecture Foundation:** Routing, state, theming, data-fetch established
3. ✅ **Component Library:** Reusable, well-documented components
4. ✅ **Development Workflow:** Hot reload, linting, building all functional
5. ✅ **Documentation:** Complete technical documentation

### Phase 2 Success Criteria - 🔄 IN PROGRESS
1. 🔄 **Dark Mode:** Complete theme system with instant toggle
2. 🔄 **Full Integration:** All backend APIs functional with proper error handling
3. 🔄 **End-to-End Workflows:** Users can complete all tasks without errors
4. 🔄 **Performance:** Lighthouse scores ≥ 85 across all metrics
5. 🔄 **Production Ready:** Comprehensive testing and monitoring

### Definition of Done - Extended Sprint
- [ ] All backend APIs implemented and tested
- [ ] Dark mode fully functional with user preference persistence
- [ ] WebSocket integration for real-time updates
- [ ] Thumbnail service operational
- [ ] Performance audit completed with scores ≥ 85
- [ ] Unit test coverage ≥ 80%
- [ ] End-to-end user workflows tested and documented
- [ ] Production deployment pipeline ready

---

## 10. Timeline - Extended Sprint

### ✅ Phase 1 Complete (Weeks 1-2)
- ✅ Frontend UI development
- ✅ Component library creation
- ✅ State management implementation
- ✅ Basic API integration framework

### 🔄 Phase 2 In Progress (Weeks 3+)
**Week 3: Core Integration**
- [ ] Dark mode implementation
- [ ] Backend collection API
- [ ] Backend health endpoints

**Week 4: Advanced Features**
- [ ] Ingestion API integration
- [ ] Search API integration
- [ ] Thumbnail service

**Week 5: Real-time & Polish**
- [ ] WebSocket integration
- [ ] Performance optimization
- [ ] Comprehensive testing

**Week 6+: Production Readiness**
- [ ] Advanced features (bulk operations, filters)
- [ ] Monitoring and analytics
- [ ] Deployment pipeline

---

*Sprint Status:* 🔄 **EXTENDED SPRINT IN PROGRESS**  
*Phase 1:* ✅ **COMPLETED** - Frontend UI fully functional  
*Phase 2:* 🔄 **IN PROGRESS** - Backend integration and dark mode  
*Next Review:* Weekly until completion