# Frontend Pipeline Analysis & Next Steps

*Document created: 17 June 2025*

---

## 🎯 Current State Snapshot

### ✅ Strengths
1. **Rule-Driven Codebase** – Follows Sprint-10 component / hydration / React-Query rules → consistent patterns.
2. **Modern Stack** – Next.js 15 app-router, Chakra semantic tokens, React Query v5.
3. **Hydration Safety** – `'use client'`, mounted checks, minimal SSR css; no console mismatches in prod build.
4. **Real-Time UX** – Job-status polling with progress, drag-and-drop search experience.

### ⚠️ Limitations
* No automated testing ⇒ regressions likely.
* Duplicate `next.config` files – potential build confusion.
* Some remaining "God-component" smell (`app/page.tsx` ~430 LOC).
* Error handling scattered – some `.catch` swallowed.
* Performance tooling not yet wired (bundle size ≈ 270 kB gzip but unverified after future growth).

---

## 🔍 Detailed Analysis

| Layer | Observation | Impact | Fix |
|-------|-------------|--------|-----|
| **Routing / Layout** | Duplicate configs (`.mjs` & `.ts`) | Build warnings, plugin duplication | Remove `.ts` or merge content |
| **State** | A few imperative Axios calls (e.g. `CollectionModal`) bypass React Query | Cache inconsistency | Refactor to `useMutation` hooks |
| **UI Composition** | Home page mixes logic & UI | Harder to test, slower re-renders | Split into smaller containers per rule set |
| **API Constants** | `process.env.NEXT_PUBLIC_API_URL` used in some places but hard-coded `http://localhost:8002` in others | Deployment friction | Export `API_HOST` from `lib/config.ts` |
| **Assets** | No `public/` images yet – hero uses inline icon | OK now; will grow | Evaluate Next.js remoteImages config when backend hosts originals |
| **Accessibility** | Chakra defaults help, but custom components lack aria labels | Potential a11y issues | Lighthouse a11y audit |

---

## 🚀 Proposed Next Steps

1. **Testing Foundation**
   * Add Jest + React-Testing-Library & MSW; write tests for `useSearch`, `SearchInput`, `CollectionModal`.
2. **Config Consolidation**
   * Merge `next.config.ts` into `next.config.mjs`; centralise API host & image domains.
3. **Component Decomposition**
   * Extract `Sidebar`, `HeroSection`, `FeaturedActions`, `SetupProgress` from `app/page.tsx`.
4. **Global Error Boundary + Sentry**
   * Wrap `app/layout.tsx` children; capture unhandled errors → toast + remote logging.
5. **Performance & Bundle Audit**
   * `npx @next/bundle-analyzer` post-build; lazy-load `ImageDetailsModal`, framer-motion heavy components.
6. **Infinite Scroll Search**
   * Convert grid to `useInfiniteQuery` + intersection observer; offload pagination to backend.
7. **Duplicate Detection UI**
   * Add `/duplicates` page; display clusters; use polling until job complete.
8. **Accessibility Pass**
   * Focus traps in modals; aria-labels on buttons; colour contrast tokens check.
9. **CI Pipeline**
   * GitHub Actions: `lint`, `test`, `next build`, Lighthouse CI.

---

## 🏆 Success Metrics

| Goal | Target |
|------|--------|
| Lighthouse Performance | ≥ 85 |
| Lighthouse Accessibility | ≥ 90 |
| Unit-test coverage | ≥ 70 % lines |
| Bundle size (JS, gzip) | ≤ 300 kB initial |
| Core Web Vitals | All in green |

---

## 📅 4-Week Execution Plan

| Week | Focus | Deliverables |
|------|-------|-------------|
| 1 | **Testing & Config** | Jest setup, 10+ component tests, config cleanup done |
| 2 | **Refactor & Error Handling** | Decompose Home page, introduce error boundary, Sentry hooked |
| 3 | **Performance** | Bundle audit, lazy-load heavy modules, InfiniteScroll search |
| 4 | **Feature & A11y** | Duplicate-detection UI, a11y fixes, CI pipeline with Lighthouse CI |

---

## Revision History

| Date | Author | Notes |
|------|--------|-------|
| 2025-06-17 | AI Assistant | Initial next-steps analysis for frontend | 