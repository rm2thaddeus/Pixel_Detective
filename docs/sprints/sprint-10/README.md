# Sprint 10 – Critical UI Refactor / Vertical-Slice v0.1

Welcome to **Sprint 10**!  In this sprint we will deliver the first production-ready slice of the new **Next.js + TypeScript** frontend that talks directly to our FastAPI backend services.  This README is your single-page orientation guide.

---

## 1. Why This Sprint Exists
The Streamlit interface was removed in Sprint 09.  Users currently need to hit the backend with cURL or the CLI.  Our goal is to restore a **modern, real-time UI** that:
1. Exercises *every* critical backend endpoint.
2. Establishes reusable React patterns (routing, state, data-fetch, theming).
3. Provides a thin but valuable end-user experience (collection management, ingestion, search, live logs).

---

## 2. High-Level Objectives
| ID | Objective | Success Metric |
|----|-----------|---------------|
| O-1 | Home screen shows backend health & active collection | Banner turns green when `/` responds 200 OK |
| O-2 | Collection management UI | User can list, create, select collections |
| O-3 | Add-Images flow with live progress | Folder path → ingestion job → progress bar to 100 % |
| O-4 | Search MVP | Text prompt → grid of top-N images |
| O-5 | Architectural foundations in place | Next.js app boots, React-Query/Zustand/Chakra configured |
| O-6 | CI smoke-test pipeline | GH Actions build + contract test passes |

---

## 3. Deliverables Checklist
- [ ] `frontend/` Next.js project scaffold
- [ ] **Home** page with health & collection summary
- [ ] **CollectionsModal** for create/select
- [ ] **AddImagesModal** + Loading/Logs page
- [ ] **Search** page (prompt + results grid)
- [ ] `lib/api.ts` (typed axios wrapper) & `store/` Zustand slices
- [ ] Socket.IO client stub (`lib/socket.ts`)
- [ ] ESLint + Prettier + Jest config
- [ ] GitHub Action workflow (`.github/workflows/ci.yml`)
- [ ] Documentation: PRD, Tech Plan, Quick Reference, Completion Summary

---

## 4. Timeline (2-Week Sprint)
| Day | Milestone |
|-----|-----------|
| D0 | Project scaffold, tooling, CI skeleton |
| D1-2 | API client & state slices |
| D3-4 | Home & Collection workflow |
| D5-6 | Add-Images flow & Logs panel |
| D7-8 | Search MVP |
| D9 | Polish, a11y, Lighthouse audit |
| D10 | Buffer / bug-fix / demo prep |

---

## 5. Getting Started (TL;DR)
```bash
# 0. Prerequisite – backend services running on ports 8002 / 8001
# 1. Setup frontend
cd frontend
npm install
npm run dev
# 2. Open http://localhost:3000
```
Environment variables:
```
NEXT_PUBLIC_API_URL=http://localhost:8002
NEXT_PUBLIC_SOCKET_URL=http://localhost:8002  # placeholder for Sprint 11
```

---

## 6. Team & Roles
| Role | Name |
|------|-------|
| Frontend Lead | You (junior dev) – focus on UI & state |
| Backend Advisor | Senior dev / AI assistant |
| DevOps Support | TBD |

---

## 7. Where to Dive Deeper
1. **`PRD.md`** – formal requirements & acceptance criteria.
2. **`technical-implementation-plan.md`** – step-by-step tasks with file paths.
3. **`docs/sprints/critical-ui-refactor/*`** – original long-form blueprint.
4. **`backend/ARCHITECTURE.md`** – source of truth for API contracts.

Good luck – and remember to document every significant decision in the sprint folder! 