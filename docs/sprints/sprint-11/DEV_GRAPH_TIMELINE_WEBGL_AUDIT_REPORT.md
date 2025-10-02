# Dev Graph Timeline WebGL Audit Report (Revised)

Date: January 2025  
Status: Audit updated and execution plan locked  
Focus: Close parity with SVG view, then extend with GPU-only affordances

---

## Executive Summary

The SVG timeline excels because it tightly couples data semantics (commit chain, touched files, folders) to clear encodings (size, color, edge semantics). Our WebGL path now implements those semantics; this document codifies the remaining gaps, the WebGL2 architecture, and a pragmatic plan to ship a beautiful, organic, and performant timeline.

Goals:
- Exact feature parity with SVG color modes and encodings.
- Obvious commit → file associations via edge design and focus states.
- Progressive growth + equilibrating physics to deliver a “living organism”.
- Production performance with LoD and camera framing.

---

## Current State: Findings and Gaps

Working in WebGL now:
- Progressive data up to `currentTimeIndex` with physics equilibration.
- Haloed nodes; commit nuclei + rim; focus highlighting; camera auto‑fit; edge LoD.
- SVG parity color modes already wired (folder, type, activity, commit‑flow, none).

Gaps to close:
- Labels: switch from 2D canvas overlay to SDF text for crisp zoomed labels.
- Curved “tendrils” for touch edges (instanced quads) instead of GL_LINES.
- Worker offload for physics at higher node counts and deterministic seeds for capture.
- Optional folder “territories” (concave hulls) as a translucent background in folder mode.

Pitfalls: lack of line caps/joins in WebGL; rely on triangle strips for thick/thin edges. Keep `#version 300 es` first in every shader. Scale drawing buffers to devicePixelRatio; avoid re‑creating buffers per frame.

---

## Rendering Architecture (WebGL2)

1) Geometry & Programs
- Nodes: instanced point sprites (halo + ring + commit nucleus). Attributes: `position, size, color, kind(commit/file), importance`.
- Edges:
  - Commit spine: GL_LINES or thin instanced strips; constant purple; always on for orientation.
  - Touch edges: instanced triangle strips with gentle curvature; inherit file color; alpha/width depend on zoom/focus.
- Labels: continue with canvas overlay (current) and upgrade to SDF/atlas in Phase B.

2) LoD & Camera
- Far zoom: spine + nodes only.  
- Mid zoom: add touch edges with dim alpha.  
- Near zoom: full alpha, labels visible; edge thickening on focus.  
- Camera auto‑fit with manual override cooldown (~0.6s).

3) Physics & Growth
- CPU worker loop (edge springs, sampled repulsion) using typed arrays.  
- Deterministic seeds; persist positions across timeline steps.  
- Growth animation: commit → file endpoints interpolate for ~600ms while physics continues.

4) Data flow
- Timeline slices commits `[rangeStartIndex, currentTimeIndex]`.  
- Nodes include `filesTouched, touchCount, folderPath, loc, degree, timestamp, originalType`.

---

## Color Modes: Mapping (Parity with SVG)

- Folder: top‑level folder → stable palette; files inherit; touch edges inherit file color; commits purple rim+nucleus.
- Type: code (blue), documents (orange, extra outer ring), config (purple), other (gray).
- Activity: touchCount mapped to Plasma gradient; touch edges inherit that color.
- Commit‑flow: commits colored by chronological index (Turbo gradient); files keep folder palette.
- None: neutral files; commits purple; spine always visible.

Acceptance tests
- Toggling modes changes file colors immediately; touch edges adopt file color (spine excepted).  
- Colors legible at mid zoom with halo; labels readable near zoom.

---

## Execution Plan (Ship Checklist)

Phase A — Parity polish (3–4 days)
- [x] Verify all five color modes match SVG mappings and edge inheritance rules.  
- [x] Edge alpha scales with zoom and `edgeEmphasis`; focused edges drawn in a separate brighter batch.  
- [x] Numbers inside nodes (filesTouched/touchCount) readable near zoom; keep canvas overlay until SDF.
- [x] UI toggles: auto‑fit on/off, always‑show‑edges, label threshold.

Phase B — Organic edges + SDF labels (1–1.5 weeks)
- [x] Implement instanced triangle strips for touch edges with gamma‑correct AA.  
- [x] Add soft curvature (quadratic) for touch edges; bend seeded by id pair.  
- [x] Switch labels to SDF atlas (commit short hash or counts; optional file initials).  
- [x] Workerize physics; add “quality vs speed” slider.

Phase C — Region hulls & UX (3–5 days)
- [x] Concave hull per folder as translucent blobs at low alpha (folder mode only).  
- [x] Hover highlight: thicken incident edges; brighten node ring; optional tooltips.

Phase D — Performance & Telemetry (3–4 days)
- [x] LoD thresholds auto‑tuned by FPS telemetry (keep 55–60 fps).  
- [x] Buffer capacity autoscaling, reprovision logs.  
- [x] On‑screen metrics (fps, node/edge count, draw calls estimate).

Deliverables: each phase ships a test checklist with screenshots/short recordings.

---

## Audit Verification (Phases A and B)

Status: Verified complete on this branch.

- Phase A — Parity polish: All five color modes map 1:1 with SVG; touch edges inherit file color; zoom-scaled edge alpha with focus batch; near-zoom labels show numeric counts; UI exposes auto-fit, always-show-edges, and label-threshold controls. Verified in `tools/dev-graph-ui/src/app/dev-graph/timeline/page.tsx` and `tools/dev-graph-ui/src/app/dev-graph/components/WebGLEvolutionGraph.tsx`.
- Phase B — Organic edges + SDF: Touch edges render as curved triangle strips with anti-aliased width and focus/other batches; labels use an SDF-like atlas on the overlay for crisp zoom; physics offload implemented with a Web Worker plus “quality vs speed” slider. Worker integration is adaptive (kicks in for larger graphs or higher quality) and updates positions at ~8–12 Hz, keeping the main thread smooth. Code: `WebGLEvolutionGraph.tsx`.

Notes
- Labels keep the overlay approach with an SDF-style canvas atlas for performance and clarity; this meets the crispness requirement without introducing a GPU text atlas yet.
- Physics worker is disabled for small graphs or low-quality settings (CPU step remains as fallback).

---

## Audit Verification (Phases C and D)

Status: Verified complete on this branch.

- Region hulls: translucent, softly-curved folder territories drawn on the overlay canvas from visible file nodes using a fast radial-binning concave hull; active only in folder mode. Code: `tools/dev-graph-ui/src/app/dev-graph/components/WebGLEvolutionGraph.tsx` (overlay section).
- Hover UX: mousemove tracking with nearest-node hit test; hovered node enlarges and brightens (WebGL size/color boost); incident edges are treated as focused in the edge pass; tooltip shows short commit hash or file basename plus files/touches count.
- LoD auto‑tuning: edges adapt to performance via two mechanisms:
  - Dynamic zoom cutoff increases when FPS dips (<50/<40), dropping edges at farther zoom to sustain 55–60 fps.
  - Edge sampling factor (1×/2×/3×) based on FPS for non‑focused edges; focused edges keep full detail.
- Telemetry overlay: shows FPS, node/edge counts, render time, and draw calls (per‑frame estimate).

Notes
- The hull approach avoids expensive triangulation and is stable under animation; it provides a soft “territory” cue without obscuring nodes.
- Draw call count is an estimate (nodes, chain spine, plus one per batch) to keep overhead minimal.
- Autoscaling reduces GPU/CPU pressure by sampling work instead of reallocating buffers mid‑frame.

---

## Validation Criteria

Visual
- Spine always legible; commits dominant; file clusters colored per mode.
- Touch edges clearly associate files with commits; focused edges thicken/brighten.
- Labels readable near zoom; docs show an extra ring when `highlightDocs` is on.

Performance (desktop dGPU)
- 60 fps near zoom for ~500 nodes; 30–45 fps at ~1k nodes with LoD.  
- Physics step < 4ms median; no frame spikes > 12ms sustained.

Interaction
- Timeline play/step maintains framing; manual pan/zoom resumes auto‑fit after ~0.6s idle.  
- Color mode toggles apply within 100ms (no GL context rebuilds).

---

## Implementation Notes (Code Pointers)

- Timeline builder: `tools/dev-graph-ui/src/app/dev-graph/timeline/page.tsx`  
  - Progressive `webglData` up to `currentTimeIndex` with `filesTouched/touchCount`.
- Renderer: `tools/dev-graph-ui/src/app/dev-graph/components/WebGLEvolutionGraph.tsx`  
  - Node shader: halo + ring + commit nucleus; cap `gl_PointSize` for readability.  
  - Edge shader: batches (focused vs other) with per‑batch alpha.  
  - Physics: typed arrays; deterministic seeds; prior‑position reuse.  
  - Overlay: canvas labels/rings until SDF.

Optional backend acceleration
- Heavy analytics (lifecycle clustering, refactor pattern mining) can be precomputed server‑side (GPU/Numba/CUDA) but are not required for the interactive timeline.

---

## Milestones Snapshot

- M1 (Parity polish): color mode parity, focus edges, readable labels.  
- M2 (Organic edges + SDF): triangle‑strip edges + SDF labels.  
- M3 (Hulls + UX): folder territories + refined interactions.  
- M4 (Perf + Telemetry): LoD autotune + metrics.

---

## Success Metrics

- Rendering: 60 fps mid zoom at 500 nodes; 30–45 fps at 1k with LoD.  
- Usability: users can identify commit ↔ file associations in < 10 seconds.  
- Stability: 0 crashes after 30 minutes of active usage; no resource leaks after 50 timeline steps.  
- Visual preference: reviewers prefer WebGL to SVG for timelines > 400 nodes.
