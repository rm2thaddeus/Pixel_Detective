# Pixel Detective Frontpage Design Plan

**Date:** 2026-02-03
**Location:** `site/`
**Audience:** Hiring managers and recruiters (portfolio-first, technical credibility)

## Goals
- Create a multi-page, static site that showcases Pixel Detective and Dev Graph with depth and credibility.
- Provide a narrative entry point (Manifesto comic) and direct paths into technical detail.
- Use a bold, premium visual language that still reflects the existing Pixel Detective brand.
- Keep the site easy to run (no build step required).

## Information Architecture (Order)
1. Home
2. Manifesto
3. Pixel Detective
4. Dev Graph

## Visual Direction
**Theme:** Optical Lab / Signal Cartography
- Grid overlays, contour rings, dot clouds, and subtle grain.
- Precise typography and crisp hierarchy.
- Scientific instrumentation aesthetic with editorial polish.

## Typography
- Headings: IBM Plex Serif
- Body: IBM Plex Sans
- Code/metrics: IBM Plex Mono

## Color System (Draft)
- Signal Blue (primary)
- Ion Teal (secondary)
- Graphite Ink (text)
- Parchment (base surface)

## Page Content Summaries

### Home
- Hero: UMAP-inspired visual, clear statement of what Pixel Detective is.
- Query Flow: text/image -> embedding -> vector DB -> ranked results.
- Credibility band: GPU-accelerated UMAP, microservices, production-ready UI.
- CTA tiles: Manifesto, Pixel Detective, Dev Graph.
- Planning DNA: sprint/PRD/roadmap discipline.

### Manifesto (Comic Narrative)
Panels: Spark, Promptcraft, Prototype, Refactor, System, Stewardship.
- Short narrative blocks and artifact callouts per panel.
- Links to docs/sprints as evidence trail.

### Pixel Detective
- Problem statement and product solution summary.
- Architecture pipeline: Frontend -> Ingestion -> ML Inference -> Qdrant -> GPU UMAP.
- Systems sections: Search Pipeline, Latent Space Explorer, Curation & Duplicates, Performance.
- Metrics callouts pulled from docs.

### Dev Graph
- Developer Graph concept and why it matters.
- Architecture: Git history + Neo4j -> API -> UI.
- Features: nodes/relations, temporal slices, sprint mapping.

## Visual Assets (Generated)
- `site/assets/images/hero-umap.png`
- `site/assets/images/query-flow.png`
- `site/assets/images/pd-architecture-hero.png`
- `site/assets/images/pd-latent-space.png`
- `site/assets/images/pd-curation.png`
- `site/assets/images/dev-graph-hero.png`
- `site/assets/images/dev-graph-timeline.png`
- `site/assets/images/manifesto-panel-1.png`
- `site/assets/images/manifesto-panel-2.png`
- `site/assets/images/manifesto-panel-3.png`

## Implementation Plan (Static Site)
1. Create `site/` with shared assets folder and CSS.
2. Build a shared layout (nav, footer, typography, grid system).
3. Implement Home with hero, query flow, credibility band, CTA tiles.
4. Implement Manifesto as a vertical comic sequence with panel frames and captions.
5. Implement Pixel Detective page with architecture diagram, system cards, metrics.
6. Implement Dev Graph page with graph visuals, features, and impact narrative.
7. Add light JS for intersection reveal and small motion cues.
8. Ensure responsive layout for mobile.

## QA Checklist
- All pages render locally by opening `site/index.html`.
- Links between pages work.
- Images load and scale correctly.
- Mobile layout is readable (no horizontal scroll).
- Text contrast meets accessibility.

## Notes
- Real data visuals can later be replaced with exports via `pixel-detective-exports`.
- This plan is the audit trail for future updates.
