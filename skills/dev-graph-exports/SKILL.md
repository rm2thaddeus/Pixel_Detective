---
name: dev-graph-exports
description: Export Dev Graph UI assets and dashboard data. Use when the user asks for structure SVG exports, timeline SVG/MP4 exports, per-commit SVGs, sprint-linked visuals, or dashboard/analytics JSON from the Dev Graph API.
---

# Dev Graph Exports

Generate exportable assets that match the Dev Graph UI.

## Requirements
- Dev Graph API running on `http://localhost:8080`
- Node.js available (for SVG-parity renderer)
- Dependencies installed in `tools/dev-graph-ui`:
  - `npm --prefix tools/dev-graph-ui install jsdom @resvg/resvg-js`
- ffmpeg available on PATH for mp4/gif exports

## Exports

### Structure SVG (UI export)
- Script: `python skills/dev-graph-exports/scripts/export_structure_svg.py`
- Output default: `exports/dev-graph/structure-graph.svg`
- Optional: `--url http://localhost:3001/dev-graph/structure --output <path>`
- Filters: `--source-type File --target-type Document --relation-type CONTAINS_CHUNK --max-nodes 250`

### Timeline MP4 + GIF segments (SVG-parity, API only)
- Script: `node skills/dev-graph-exports/scripts/export_timeline_segments_svg_parity.js`
- Output default: mp4 + gif plus per-commit SVG frames under `exports/dev-graph/timeline-frames/`
- The SVG frames are the primary artifacts; raster frames are temporary and removed after encoding.
- Segments: commits 1-70, 70-200, 200+.
- Key options:
  - Range: `--range-start 0 --range-end 69` (single segment)
  - Segments: `--segments "0-69,69-199,199-"` (dash with empty end means "to last")
  - Graph density: `--max-nodes 400` (increase if you want file/folder nodes attached to commits)
  - Node layout: `--show-folder-groups true|false`, `--focused-view true|false`, `--size-by-loc true|false`
  - Styling: `--color-mode folder|type|commit-flow|activity|none`, `--highlight-docs true|false`, `--edge-emphasis 0.0-1.0`
  - Filtering: `--active-folders "backend,frontend"`, `--include-patterns "docs,/\\.md$/"`
  - Canvas size: `--width 1200 --height 600`
  - Data volume: `--limit 5000 --max-files 50` (API request options)

### Per-commit SVG frames
- Script: `python skills/dev-graph-exports/scripts/export_timeline_svgs.py`
- Output default: `exports/dev-graph/timeline-frames/`
- Optional: `--start 0 --count 20`

### Dashboard data
- Script: `python skills/dev-graph-exports/scripts/export_dashboard_data.py`
- Output default: `exports/dev-graph/dashboard/`

## Notes
- Timeline exports must use the SVG timeline renderer, not the GL2 timeline view.
- The SVG-parity exporter uses the Dev Graph API only; UI is not required.
- Structure export is taken from the main Structure View canvas and reflects current filters.
- Dashboard exports pull from `/api/v1/dev-graph/stats`, `/analytics`, `/quality`, and `/data-quality/overview`.
- Use `sprints.json` from dashboard exports to link frames and videos to sprint windows.
