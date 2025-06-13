# Sprint 10 – Product Requirements Document (PRD)

> **Codename:** _Critical UI Refactor – Vertical-Slice v0.1_
> **Duration:** 2 weeks (T-0 → T-10)  
> **Prepared for:** Junior Development Team  
> **Related Docs:** [`technical-implementation-plan.md`](./technical-implementation-plan.md), [`README.md`](./README.md)

---

## 1. Executive Summary
Sprint 10 will deliver the first usable React/Next.js interface that re-establishes day-to-day usability lost when the Streamlit UI was removed in Sprint 09.  The scope is intentionally narrow but touches every critical backend pathway:

* System health display  
* Collection management (list / create / select)  
* Folder ingestion with live progress & logs  
* Basic vector search & result display  

This slice proves the new stack, exposes integration gaps early, and sets up incremental feature growth in Sprint 11+.

---

## 2. Goals & Non-Goals
### 2.1 Goals – must ship
1. **Operational UI** that a non-technical user can navigate end-to-end without cURL.
2. **Shared frontend architecture** – routing, state, theming, data-fetch, linting, CI.
3. **Live feedback loop** – job progress & logs surfaced in near-real-time (HTTP polling).
4. **Documentation & CI** – sprint docs complete; GitHub Action builds and fails on contract breakage.

### 2.2 Out of Scope (deferred)
* Latent Space visualisation, AI Guessing Game, Duplicate Detection UI.  
* WebSocket upgrade for logs (planned Sprint 11).  
* Desktop/Electron packaging & native folder picker.

---

## 3. User Stories & Acceptance Criteria
| ID | User Story | Acceptance Criteria | Priority |
|----|------------|--------------------|----------|
| FR-10-01 | As a user I open the web app and instantly see if backend services are healthy | Banner shows ✅ when both `/` (8002) & `/` (8001) return 200.  Error banner if not. | High |
| FR-10-02 | I can view, create, and select collections | List shows names from `GET /collections`.  Create sends `POST /collections`.  Selecting fires `POST /collections/select` and UI state updates. | High |
| FR-10-03 | I can ingest images from a local folder and watch progress | Path input ➜ `POST /ingest/` returns job_id ➜ Logs page polls `/ingest/status/{id}` every 1 s ➜ progress bar fills, logs stream, "Done" toast when status==completed. | High |
| FR-10-04 | I can search my collection with a text prompt | Prompt ➜ encode on backend via `/search` ➜ grid renders top-10 results with thumbnail, filename, caption, score. | High |
| NFR-10-01 | App loads quickly | First Contentful Paint ≤ 2 s on dev box. | Medium |
| NFR-10-02 | Code quality & CI | ESLint passes, unit tests ≥ 90 % green; GitHub Action fails build on regression. | Medium |

---

## 4. Functional Requirements Matrix
1. **Health Banner**  
   * _Endpoint:_ `GET /` (8002) & `GET /` (8001)  
   * _Fail state:_ show red banner with retry button.
2. **Collection Modal**  
   * List collections: `GET /collections`  
   * Create collection: `POST /collections` (`{collection_name}`)  
   * Select: `POST /collections/select`.
3. **Add Images Modal**  
   * POST `/ingest/` (`{directory_path}`)  
   * Redirect to Logs page.
4. **Logs Page**  
   * Poll GET `/ingest/status/{job_id}`  
   * Render `progress`, append `logs[]`.
5. **Search Page**  
   * POST `/search` with `{embedding: <text>, limit:10}`  
   * Display `payload.filename`, `payload.caption`, `score`.

---

## 5. Non-Functional Requirements
* **Performance:** FCP ≤ 2 s; interactive ≤ 500 ms for search.  
* **Accessibility:** Hit Lighthouse a11y ≥ 90 (Chakra UI helps).  
* **Security:** Browser CORS only (service-to-service API-key tackled later).  
* **Dev Experience:** `npm run dev` hot-reload <1 s; ESLint + Prettier mandatory.

---

## 6. Metrics & KPIs
| Metric | Target |
|--------|--------|
| Build success rate | 100 % on `main` branch |
| Lighthouse Perf | ≥ 85 |
| Lighthouse a11y | ≥ 90 |
| End-to-end ingest demo | ≤ 3 min for 25-image sample |

---

## 7. Dependencies
* FastAPI services running locally (`docker-compose up backend`)  
* Qdrant container up and seeded (handled automatically by ingest).  
* Node ≥ 18, npm ≥ 9.

---

## 8. Open Questions / Future Considerations
* Thumbnail delivery mechanism – backend `/thumbnail/{id}` endpoint vs `file://` paths?  
* How to surface image binary in web-safe way for remote deployments.  
* WebSocket channel contract – JSON schema, auth?  
* Do we migrate to TanStack Router once beta stabilises?

---

## 9. Approval
| Role | Name | Date | Sign-off |
|------|------|------|----------|
| Product Owner | TBD |  |  |
| Tech Lead | TBD |  |  |
| QA | TBD |  |  |

*Fill and commit during sprint kickoff.* 