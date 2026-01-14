Skills Scope Notes

This folder contains skill definitions and helper scripts for Pixel Detective and Dev Graph. This README captures what was scoped, built, and validated in the current session, plus a forward plan.

What is scoped and implemented
- Start Pixel Detective: automated startup for docker-only, backend-only, and full stack (backend + frontend). Includes status/stop and optional page open.
- Start Dev Graph: automated startup for docker-only, backend-only, and full stack (backend + frontend). Includes status/stop.
- Docker helper: inventory and health checks for running containers.
- Sprint summary PDF: generate a PDF with cards from docs/sprints content (drops output per sprint folder).
- Dev Graph exports: standalone, API-only SVG parity exporter for timeline animations, plus structure SVG and dashboard JSON exports.

What was validated
- SVG timeline exporter generates MP4 + GIF per segment and per-commit SVG frames.
- Segments produced for 1-70, 70-200, and 200+ commits (200-290 for this repo).

Key design decisions
- Timeline exports must use the SVG timeline renderer (not GL2/WebGL).
- No artificial node limits by default (max-nodes=0, max-files=0).
- Auto-fit and smooth zoom motion are enabled by default.
- If a render fails, the exporter retries at a smaller canvas size.

Plan (next steps)
1. Pixel Detective: verify start scripts on this machine; add a small health check endpoint test and a "ready" summary.
2. Sprint PDF: align visuals with the frontend theme (type, colors, card layout) and add snapshots if available.
3. Dev Graph exports: add a "cinematic pull-back" mode (optional), and a preset for "sprint window" exports tied to sprints.json.
4. Documentation: create a short "how to use skills" quickstart and add examples in each SKILL.md.
