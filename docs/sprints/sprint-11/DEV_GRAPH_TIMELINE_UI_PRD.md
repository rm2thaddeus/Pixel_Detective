# Dev Graph Timeline — PRD (UI/UX + Backend Contracts)

## Problem

The current timeline view caps the commit range at 200 items and the visual encodings don’t clearly communicate hierarchy, document importance, or commit flow. Edge rendering can overpower node semantics at higher zoom levels, and document nodes (e.g., sprint docs) collapse into folders, making them hard to track.

## Goals

- Allow selecting and playing back the full commit range available in the repository.
- Improve readability and meaning of the graph at every zoom level.
- Always surface document nodes (e.g., sprint markdown files) and visually highlight them.
- Reduce visual noise from edges while preserving navigational context of the commit chain.

## Scope (v1)

1) Backend: expand the evolution timeline endpoint to return up to 5,000 commits so the UI can span all commits in most repos.
2) Frontend: update timeline page to:
   - Load up to 5,000 commits, initialize range to the full set, and show precise “Showing commits X–Y of N total”.
   - Keep existing “Auto node budget”, “Folders”, “Focus”, “Zoom”, and LOC toggles.
3) Frontend graph (ProgressiveStructureGraph):
   - Size = lines of code (LOC) for files/folders/commits (sum for commit nodes).
   - Color modes (user selectable):
     - By Folder: categorical color by top‑level folder (default).
     - By Type: code/document/config/other via fixed palette.
     - Commit Flow: temporal gradient along commit chain.
     - By Activity: files colored by how many commits touched them.
     - Neutral: gray/amber neutrals.
   - Document files: never collapse into folders; render as standalone nodes and draw a complementary color ring to highlight (toggleable).
   - Edges: user‑controlled “Edge Emphasis” slider; chain vs file links scale width/opacity appropriately.

## Non‑Goals (v1)

- Full time-scrubbing filter over the entire subgraph (kept for future work).
- Server‑side pagination for >5k commits (not needed for this repo size).

## UX Details

- Controls retain the existing layout and labels. “Color by LOC” now toggles between Viridis (ON) and folder‑based categorical coloring (OFF).
- Commit range slider reflects the full commit count; no hard 200 limit. Playback buttons honor the selected range.
- Document nodes (markdown/txt/rst) always render individually; folder grouping skips them. They receive a thin outer ring using the complementary color of their fill to pop against the dark background.
- Edge styling:
  - Commit chain: opacity ~0.6, width 2px.
  - File links: opacity ~0.08, width 0.6px, dashed. Edges render beneath nodes.

## Data/Contracts

- GET `/api/v1/dev-graph/evolution/timeline?limit={1..5000}&max_files_per_commit={1..200}`
  - Returns: `commits[]`, `file_lifecycles[]`, `total_commits`.
  - No shape changes; only raised `limit` upper bound.

## Acceptance Criteria

- Timeline range slider supports selecting the entire set of commits (no 200 cap).
- With “Color by LOC” off, files/folders are colored by their top‑level folder. With it on, they use a LOC scale.
- Commit nodes clearly show a temporal gradient; direction is readable when zoomed in.
- Document nodes are always visible (not folded into folders) and have a complementary outline.
- Edges feel secondary; nodes carry the primary visual weight.

## Implementation Notes

- Backend: increase query param upper bound to 5,000 (FastAPI `le=5000`). Keep `max_files_per_commit` cap for payload control.
- Frontend: request `limit=5000` for this view. Initialize range to `[0, commits.length-1]`.
- Graph:
  - Folder color scale (Tableau10) keyed by top‑level folder.
  - Color modes wired to the control bar; commit gradient only when “Commit Flow” is selected.
  - Activity mode colors files by touch count across the visible range.
  - Documents always visible; complementary `.doc-ring` outline (toggleable).
  - Edge widths/opacities respond to the Edge Emphasis slider.

## Risks

- Very large repositories may hit UI perf limits even with node budget controls; the auto‑budget + range selection should mitigate.
- Some repos with deep path structures may produce many top‑level buckets; Tableau10 repeats after 10—acceptable for v1.

## Follow‑ups

- Time‑scrubbed subgraph filtering and commit breadcrumb overlay.
- Optional legend for top‑level folder colors.
