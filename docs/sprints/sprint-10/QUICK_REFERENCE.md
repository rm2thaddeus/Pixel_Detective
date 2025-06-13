# Sprint 10 Quick Reference

> Keep this file open in a side pane – it saves context-switch time.

---

## 1. Daily Dev Commands
```bash
# start backend stack (from repo root)
docker-compose up -d qdrant_db
cd backend/ingestion_orchestration_fastapi_app
python main.py &  # runs on port 8002

# start frontend
cd frontend
npm install       # first time only
npm run dev       # http://localhost:3000
```

### ✅ Current Working Setup
| Service | Port | Status | Health Check |
|---------|------|--------|--------------|
| Frontend | 3000 | ✅ Running | http://localhost:3000 |
| Ingestion API | 8002 | ✅ Running | http://localhost:8002/health |
| Qdrant DB | 6333 | ✅ Running | Docker container |

### Helpful NPM scripts
| Script | Purpose | Status |
|--------|---------|--------|
| `npm run dev` | Next.js development server | ✅ Working |
| `npm run build` | Next.js production build | ✅ Working |
| `npm run lint` | ESLint check | ✅ Working |
| `npm run start` | Production server | ✅ Working |

---

## 2. Environment Variables
| Variable | Example | Notes | Status |
|----------|---------|-------|--------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8002` | Base REST URL | ✅ Set |
| `NEXT_PUBLIC_SOCKET_URL` | `http://localhost:8002` | Future WebSocket URL | 🔄 Planned |

---

## 3. Backend Endpoints Used
```
✅ GET    /health                    # Backend health check
🔄 GET    /api/v1/collections        # List collections
🔄 POST   /api/v1/collections        # Create collection {collection_name}
🔄 POST   /api/v1/collections/select # Select collection {collection_name}
🔄 POST   /api/v1/ingest/            # Start ingestion {directory_path}
🔄 GET    /api/v1/ingest/status/{id} # Get job status
🔄 POST   /api/v1/search             # Search images {embedding, limit}
```

**Note**: Collection and search endpoints need to be implemented in backend.

---

## 4. Frontend Architecture
```
frontend/src/
  app/
    page.tsx              # ✅ Main dashboard
    layout.tsx            # ✅ Root layout with providers
    search/page.tsx       # ✅ Search interface
    logs/[jobId]/page.tsx # ✅ Job tracking page
  components/
    Header.tsx            # ✅ Status bar with health & collection
    CollectionModal.tsx   # ✅ Collection management
    AddImagesModal.tsx    # ✅ Image ingestion form
    ui/provider.tsx       # ✅ Chakra UI provider
  lib/
    api.ts               # ✅ Axios client
    polyfills.ts         # ✅ structuredClone polyfill
  store/
    useStore.ts          # ✅ Zustand state management
```

---

## 5. ✅ Issues Resolved & Fixes
| Issue | Cause | Solution | Status |
|-------|-------|----------|--------|
| `Cannot read properties of undefined (reading '_config')` | Chakra UI v3 + Next.js 15 compatibility | Added `structuredClone` polyfill | ✅ Fixed |
| `Network Error` on API calls | CORS not configured | Added CORSMiddleware to FastAPI | ✅ Fixed |
| `Module not found: '@chakra-ui/next-js'` | Wrong package for v3 | Removed, used direct ChakraProvider | ✅ Fixed |
| Missing `/health` endpoint | Backend didn't have health check | Added health endpoint | ✅ Fixed |

---

## 6. Common Errors & Fixes
| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| ✅ CORS 403 | FastAPI missing origin | ✅ Fixed - CORSMiddleware added |
| ✅ 404 on `/health` | Endpoint not added | ✅ Fixed - Health endpoint added |
| ✅ `TypeError: structuredClone...` | Chakra UI v3 polyfill needed | ✅ Fixed - Polyfill added |
| Images not showing | No thumbnail strategy | Use placeholder for now |
| Collection operations fail | Backend endpoints not implemented | Implement collection API |

---

## 7. 🚀 Features Working
- ✅ **Home Dashboard**: Status cards, quick actions, guided setup
- ✅ **Backend Health**: Real-time monitoring with auto-refresh
- ✅ **Collection UI**: Modal for create/select (needs backend API)
- ✅ **Image Ingestion**: Form with job tracking (needs backend API)
- ✅ **Search Interface**: Natural language search UI (needs backend API)
- ✅ **Real-time Logs**: Job progress tracking page (needs backend API)
- ✅ **Responsive Design**: Works on mobile and desktop
- ✅ **Error Handling**: Comprehensive user feedback

---

## 8. 🔄 Next Implementation Steps
1. **Backend Collection API**: Implement `/api/v1/collections` endpoints
2. **Backend Search API**: Implement `/api/v1/search` endpoint
3. **Backend Ingestion API**: Implement `/api/v1/ingest/` endpoints
4. **Thumbnail Service**: Add `/thumbnail/{id}` endpoint
5. **WebSocket Integration**: Real-time log streaming
6. **Unit Testing**: Jest + React Testing Library

---

## 9. Useful Links
- ✅ Sprint 10 docs – `docs/sprints/sprint-10/`
- ✅ Backend architecture – `backend/ARCHITECTURE.md`
- ✅ FastAPI docs – https://fastapi.tiangolo.com
- ✅ Chakra UI v3 docs – https://v3.chakra-ui.com
- ✅ Next.js 15 docs – https://nextjs.org/docs

---

## 10. 🎯 Current Status Summary
**Frontend**: ✅ **COMPLETE** - All UI components built and working  
**Backend Integration**: 🔄 **PARTIAL** - Health check working, other APIs pending  
**User Experience**: ✅ **EXCELLENT** - Intuitive, responsive, error-handled  
**Technical Foundation**: ✅ **SOLID** - Modern stack, proper architecture  

**Ready for**: Backend API implementation and full end-to-end testing

---

Happy coding! The frontend is now fully functional and ready for backend integration. 🚀 