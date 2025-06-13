# Sprint 10 – Technical Implementation Plan

This file breaks the PRD into concrete engineering tasks, file locations, and suggested implementation details.  Treat each checklist item as *definition of done* for the corresponding user story.

---

## 0. Prep Work
- [ ] **Backend CORS patch** – Update both FastAPI apps to `app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")], ...)`.  
  _File(s):_ `backend/*_fastapi_app/main.py`  (tiny change – junior friendly).
- [ ] **/health endpoint** – trivial `@app.get("/health")` returning `{service:"ingestion",status:"ok"}` and same for ML service.  _Why:_ allows frontend to ping without auth overhead.

---

## 1. Front-End Project Scaffold (Day 0)
| Step | Command | Notes |
|------|---------|-------|
| 1.1 | `npx create-next-app@latest frontend --typescript --eslint --app` | Accept defaults; remove boilerplate pages afterwards |
| 1.2 | `cd frontend && npm i @chakra-ui/react @emotion/react @emotion/styled framer-motion @tanstack/react-query zustand axios socket.io-client` | Core libs |
| 1.3 | Add `.eslintrc`, `.prettierrc`, `.editorconfig` copied from repo templates | Consistency |
| 1.4 | Initialise Husky pre-commit hook running `npm run lint` | Prevent bad commits |

> 🛈 **Junior Tip:** Use the exact versions from `docs/sprints/critical-ui-refactor/technical-implementation-plan.md` to avoid mismatch errors.

---

## 2. Shared Layer
### 2.1 `lib/api.ts`
```ts
import axios from 'axios';
export const api = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_URL });
```
- Add **typed wrappers** using `zod` or interfaces for:
  * `getHealth()`, `getCollections()`, `createCollection()`, `selectCollection()`, `startIngest()`, `getJobStatus()`, `search()`.
- Provide React-Query hooks (`useHealth`, `useCollections`, …) inside same file or `lib/hooks.ts`.

### 2.2 `store/collection.ts`
```ts
import create from 'zustand';
interface State { active?: string; setActive: (c:string)=>void; }
export const useCollection = create<State>(set=>({ active: undefined, setActive: c=>set({active:c}) }));
```

### 2.3 `lib/socket.ts`
Stub only:
```ts
import { io } from 'socket.io-client';
export const socket = io(process.env.NEXT_PUBLIC_SOCKET_URL!, { autoConnect:false });
```
Connection will be implemented when backend exposes a channel (next sprint).

---

## 3. App Skeleton
| Path | Responsibility |
|------|---------------|
| `pages/_app.tsx` | Providers: ChakraProvider, QueryClientProvider |
| `pages/index.tsx` | Home screen – health & collection summary |
| `components/Header.tsx` | Fixed top bar with status indicator |
| `components/CollectionModal.tsx` | List/create/select collections |
| `components/AddImagesModal.tsx` | Path input & ingest trigger |
| `pages/logs/[jobId].tsx` | Poll job status, render logs |
| `pages/search.tsx` | Prompt box + ResultsGrid |
| `components/ResultsGrid.tsx` | Responsive grid using Chakra `SimpleGrid` |

> 🛈 **Improvement Idea:** isolate each "feature" (Collections, Ingest, Search) into a folder inside `features/` with UI + hooks; easier code-splitting.

---

## 4. Implementation Steps & Acceptance Tests
### 4.1 Health Banner
- Render **grey** while loading, **green** when ok, **red** on error.
- Jest test: mock 200 → banner renders `data-testid="status-ok"`.

### 4.2 Collections Workflow
- Clicking "Create Collection" opens modal → POST success → toast & refresh.
- Store updates active collection in Zustand; Header displays it.

### 4.3 Add-Images Flow
1. User enters absolute path, presses **Ingest**.
2. POST returns job_id; router.push(`/logs/${job_id}`).
3. Logs page polls status; show `progress` %, tail logs (`autoScroll` checkbox).  
   _Edge case:_ status === `failed` → red alert.

### 4.4 Search MVP
- Prompt input; on submit call `search()` mutation; display `isFetching` spinner.
- ResultsGrid card shows placeholder thumbnail (for now use `<chakra.img src={"/placeholder.png"}>`).

> 🚀 **Stretch Goal:** Use `next/fetch` with `getServerSideProps` to pre-render first page (SEO boost).

---

## 5. CI Pipeline (`.github/workflows/ci.yml`)
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Use Node 18
        uses: actions/setup-node@v4
        with: { node-version: 18 }
      - run: cd frontend && npm ci
      - run: npm run lint --workspace=frontend
      - run: npm run test --workspace=frontend
      - run: npm run build --workspace=frontend
```
Add a **contract test** step:
```yaml
      - name: Backend contract ping
        run: curl -sSf ${NEXT_PUBLIC_API_URL:-http://localhost:8002}/health
```
Runs inside a lightweight Docker compose service stub or mocks (choose later).

---

## 6. Performance & Accessibility Audit
- Use Browser-Tools MCP to run Lighthouse audit (Performance + a11y).  
- Record scores in `docs/sprints/sprint-10/PERFORMANCE_BREAKTHROUGH.md` (create if ≥10 % gain next sprint).

---

## 7. Risk Mitigation
| Risk | Impact | Mitigation |
|------|--------|-----------|
| CORS mis-config | UI cannot call backend | Patch apps with CORSMiddleware before Day-2 |
| Large image payloads | Slow search grid | Throttle to 10 results, lightweight thumbnails; plan `/thumbnail` endpoint |
| Folder picker UX | Confuses users | Provide sample path in placeholder, doc link in modal |
| Time overrun | Features slip | Tight daily stand-up + buffer pts2 |

---

*End of implementation plan – update this file as tasks are completed.* 