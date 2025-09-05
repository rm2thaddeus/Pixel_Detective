# Dev Graph Layout Modes – Exploratory PRD

Status: Exploration Ready  
Last Updated: January 2025

---

## Purpose
- Define two distinct exploratory features with clear scopes: Structure Mode (force-directed) and Time Mode (time‑radial). Avoid a single hybrid that compromises UX and performance.

## Decision Summary
- Keep modes separate with a simple UI toggle. Share filters and deep links, but optimize each mode for its primary question: “what relates to what?” vs. “what happened when?”.

---

## Feature A: Structure Mode (Force‑Directed)

- Goal: Fast, stable structural exploration (communities, hubs, neighborhoods).
- Use Cases: Cluster discovery, dependency mapping, neighborhood expansion, cross‑links.
- Non‑Goals: High‑fidelity timeline/narrative on canvas.
- UX Requirements:
  - >45 FPS pan/zoom up to ~5k visible nodes
  - Hover/select, expand/collapse neighborhood, community coloring
  - Optional edge bundling; hide labels while moving
  - Stable positions across minor filter changes
- Technical Approach:
  - Sigma.js + Graphology; ForceAtlas2 in a Web Worker
  - Early termination; resume on demand; seeded RNG for determinism
  - Coordinate reuse for similar node sets; viewport-based rendering
- Risks & Mitigations:
  - Hairball density → degree/weight edge sampling + on‑demand expansion
  - Layout thrash → partial relax for entered/removed nodes only
- KPIs:
  - TTF < 1.0s (30‑day window); >45 FPS interaction
  - Position stability score within target under minor filter changes

---

## Feature B: Time Mode (Time‑Radial Selector)

- Goal: Legible temporal storytelling and analysis (evolution over time).
- Use Cases: Sprint windows, commit bursts, feature life cycles, before/after.
- Non‑Goals: Precise spatial proximity/communities on canvas.
- UX Requirements:
  - Radial layers binned by time; inner↔outer = older↔newer
  - Focus+context on selected entity; first/last seen and change events
  - Time scrubber sync + optional playback
  - Edge throttling: show top‑N salient edges; expand on interaction
- Technical Approach:
  - Deterministic polar coordinates from time bins; angle via type/community or stable hash
  - Arc rendering with density throttles; fade inactive layers
  - Server‑side snapshot assembly for selected time windows
- Risks & Mitigations:
  - Cross‑bin edge clutter → cap edges, on‑hover expansion, bundling
  - Dense windows → auto‑coarsen bins when density threshold exceeded
- KPIs:
  - <100ms scrub responsiveness; higher temporal task success vs. Structure Mode
  - Usability/readability scores improve for “when” questions

---

## Mode Switching & Contracts
- Toggle: “Structure” | “Time”; persist last mode per user.
- Shared filters (type, sprint, search) apply consistently; semantics differ per mode.
- Deep links encode mode, query, time range, and layout seed.
- Escape hatches: node in Time → open neighborhood in Structure; node in Structure → open timeline in Time.

### Backend Contracts (Separation)
- Primary data source for both modes is `/api/v1/dev-graph/graph/subgraph` with keyset pagination (cursor `{last_ts, last_commit}`).
- Time mode additionally pairs with `/api/v1/dev-graph/commits/buckets` for density and uses the time window to constrain subgraph.
- Structure mode can optionally use server-provided `x/y` when available; otherwise apply FA2 in a worker.

---

## Validation Plan
- A/B task study: structural vs. temporal tasks per mode; measure time‑to‑answer and error rate.
- Performance profiling under target datasets; record FPS, scrub latency, jank frames.
- Qual interviews to assess mental model clarity of each mode.
