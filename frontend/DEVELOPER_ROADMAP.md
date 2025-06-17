# Frontend Roadmap – June 2025

This file aggregates upcoming technical tasks for the **Vibe Coding** web client so any contributor can see _what to tackle next and why_.  It mirrors the structure of the backend roadmap.

---

## 🟢 Recently Completed (June 2025)

1. **Full Chakra Theme Refactor** ✅  _Implemented 2025-06-17_
   *Semantic tokens introduced, dark-mode flash fixed.*  
   *Files*: `src/components/ui/provider.tsx`, `layout.tsx`.
2. **Hydration-Safe Build** ✅ _Implemented 2025-06-17_
   *All client-only files now declare `'use client'`; `ClientOnly` wrapper added.*
3. **Collection Management Pages** ✅ _Implemented 2025-06-17_
   *CRUD UI, React Query mutations, modal dialogs.*
4. **Drag-&-Drop Image Search** ✅ _Implemented 2025-06-17_
   *Search bar accepts image files; backend `/search/image` endpoint consumed.*

---

## 🔴 Critical (do these first)

1. **Test Infrastructure**  
   _Current_: No unit or integration tests.  
   _Needed_: Jest + React-Testing-Library for components; Playwright for E2E (search flow, ingestion logs).  
   _Effort_: 2–3 days.
2. **Config Clean-Up**  
   * Remove duplicate `next.config.ts` vs `next.config.mjs`.  
   * Centralise API host constants into `/src/lib/config.ts`.  
   _Effort_: 0.5 day.

---

## 🟠 High (next sprint)

3. **Storybook Adoption** – isolated component dev & documentation.  
4. **Infinite Scroll for Search** – migrate grid to `useInfiniteQuery` and intersection-observer.  
5. **Duplicate Detection UI** – leverage backend `/duplicates` endpoint; polling + results grid.
6. **Error Boundary & Sentry** – global error capture, nicer fallback UI.

---

## 🟡 Medium

7. **Performance Audit** – bundle-analyser, dynamic imports for heavy modals & code-split framer-motion.
8. **Accessibility Pass** – Lighthouse a11y score ≥ 90 ; keyboard nav & ARIA labels.
9. **PWA Support** – service-worker, offline thumbnails, add-to-home-screen meta.

---

## 🟢 Nice-to-Have / Future

10. **i18n** – `next-intl` with Spanish baseline.  
11. **Theme Customiser** – user font/spacing preferences saved locally.  
12. **Admin Settings** – toggle caption-optional mode, view backend health panel.

---

## 🧑‍💻 Skill-Set Checklist for New Contributors

* Advanced React / hooks & suspense.
* Next.js 15 App-Router & server components.
* Chakra UI theming, colour-mode.
* Data-fetching with React Query (optimistic updates, caching).
* Testing with Jest/RTL & E2E (Playwright).
* Basic REST & image upload semantics.

---

## 🛠️ Recommended Toolchain Enhancements

| Tool | Purpose |
|------|---------|
| **Storybook** | UI playground & visual regression via Chromatic |
| **msw (Mock Service Worker)** | API mocking in unit tests |
| **@next/bundle-analyzer** | JS bundle size inspection |
| **Sentry** | Runtime error monitoring |
| **Husky + lint-staged** | Pre-commit lint & test gate |

---

## 📊 Current Frontend Metrics (baseline)

| Metric | Value |
|--------|-------|
| First Contentful Paint | 0.8 s |
| Largest Contentful Paint | 1.9 s |
| Cumulative Layout Shift | 0.05 |
| Total JS (initial) | ≈ 270 kB gzip |

> _Target_: maintain all Core-Web-Vitals in the green zone after new features.

---

## Revision History

| Date | Author | Notes |
|------|--------|-------|
| 2025-06-17 | AI Assistant | Initial roadmap for frontend | 