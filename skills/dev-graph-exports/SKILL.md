---
name: dev-graph-exports
description: "Export Dev Graph UI assets and dashboard data. Use when the user asks for structure SVG exports, timeline SVG/MP4 exports, per-commit SVGs, sprint-linked visuals, or dashboard/analytics JSON from the Dev Graph API."
---

# Dev Graph Exports

Generate exportable assets that match the Dev Graph UI: structure SVGs, timeline animations, per-commit frames, and dashboard JSON.

## Quickstart

```bash
# Timeline SVG-parity export (API only, no UI required)
node skills/dev-graph-exports/scripts/export_timeline_segments_svg_parity.js --api http://localhost:8080

# Dashboard JSON export
python skills/dev-graph-exports/scripts/export_dashboard_data.py --base-url http://localhost:8080
```

## Requirements

- Dev Graph API running on `http://localhost:8080`
- Node.js 18+ (for SVG-parity renderer; uses global `fetch`)
- Dependencies: `npm --prefix tools/dev-graph-ui install jsdom @resvg/resvg-js`
- ffmpeg on PATH (for MP4/GIF exports)

## Workflow

1. **Pre-flight** — Verify the Dev Graph API is reachable: `curl -s http://localhost:8080/docs | head -1`
2. **Export** — Run the appropriate script (see Exports below).
3. **Verify** — Check that output files exist and are non-empty:
   ```bash
   ls -lh exports/dev-graph/
   ```

## Exports

### Structure SVG

```bash
python skills/dev-graph-exports/scripts/export_structure_svg.py \
  --url http://localhost:3001/dev-graph/structure \
  --output exports/dev-graph/structure-graph.svg
```

Optional filters: `--source-type File --target-type Document --relation-type CONTAINS_CHUNK --max-nodes 250`

### Timeline MP4 + GIF segments (SVG-parity, API only)

```bash
node skills/dev-graph-exports/scripts/export_timeline_segments_svg_parity.js --api http://localhost:8080
```

Output: MP4 + GIF plus per-commit SVG frames under `exports/dev-graph/timeline-frames/`. Segments default to commits 1–70, 70–200, 200+.

Common options:
- Single segment: `--range-start 0 --range-end 69`
- Sprint window: `--sprint sprint-11`
- Single SVG frame: `--frame-only true --sprint sprint-11 --sprint-frame end --frame-output <path>`
- Canvas size: `--width 1200 --height 600`

For the full list of layout, styling, filtering, and animation options, run `node skills/dev-graph-exports/scripts/export_timeline_segments_svg_parity.js --help` or see the script header comments.

### Per-commit SVG frames (UI-driven)

```bash
python skills/dev-graph-exports/scripts/export_timeline_svgs.py --start 0 --count 20
```

Output: `exports/dev-graph/timeline-frames/`. Requires the Dev Graph UI running and Python Playwright.

### Dashboard data

```bash
python skills/dev-graph-exports/scripts/export_dashboard_data.py --base-url http://localhost:8080
```

Output: `exports/dev-graph/dashboard/`. Pulls from `/api/v1/dev-graph/stats`, `/analytics`, `/quality`, and `/data-quality/overview`.

## Notes

- Timeline exports use the SVG renderer, not the GL2 timeline view.
- The SVG-parity exporter uses the API only; the UI is not required.
- Structure export reflects current filters from the Structure View canvas.
- Use `sprints.json` from dashboard exports to link frames/videos to sprint windows.
- If a segment fails, it retries at a smaller canvas size (`--downscale-on-fail true` by default).
