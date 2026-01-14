---
name: dev-graph-exports
description: Export Dev Graph UI assets and dashboard data. Use when the user asks for structure SVG exports, timeline SVG/MP4 exports, per-commit SVGs, sprint-linked visuals, or dashboard/analytics JSON from the Dev Graph API.
---

# Dev Graph Exports

Generate exportable assets that match the Dev Graph UI.

## Requirements
- Dev Graph UI running on `http://localhost:3001`
- Dev Graph API running on `http://localhost:8080`
- Playwright available for UI exports: `pip install playwright` then `python -m playwright install`

## Exports

### Structure SVG (UI export)
- Script: `python skills/dev-graph-exports/scripts/export_structure_svg.py`
- Output default: `exports/dev-graph/structure-graph.svg`
- Optional: `--url http://localhost:3001/dev-graph/structure --output <path>`
- Filters: `--source-type File --target-type Document --relation-type CONTAINS_CHUNK --max-nodes 250`

### Timeline MP4 (UI export)
- Script: `python skills/dev-graph-exports/scripts/export_timeline_mp4.py`
- Output default: `exports/dev-graph/timeline-export.mp4`
- Optional: `--url http://localhost:3001/dev-graph/timeline/svg --output <path>`

### Per-commit SVG frames
- Script: `python skills/dev-graph-exports/scripts/export_timeline_svgs.py`
- Output default: `exports/dev-graph/timeline-frames/`
- Optional: `--start 0 --count 20`

### Dashboard data
- Script: `python skills/dev-graph-exports/scripts/export_dashboard_data.py`
- Output default: `exports/dev-graph/dashboard/`

## Notes
- Timeline exports rely on MediaRecorder in the browser. If MP4 fails in headless mode, rerun with `--headful`.
- Structure export is taken from the main Structure View canvas and reflects current filters.
- Dashboard exports pull from `/api/v1/dev-graph/stats`, `/analytics`, `/quality`, and `/data-quality/overview`.
- Use `sprints.json` from dashboard exports to link frames and videos to sprint windows.
