Skills Scope Notes

This folder contains skill definitions and helper scripts for Pixel Detective and Dev Graph. This README captures what was scoped, built, and validated in the current session, plus a forward plan.

Original goals captured from this session
- Startup skills that “just work” on this machine: start docker-only, backend-only, or full stack; optionally open a specific page.
- Dev Graph exports are standalone (no UI) but require the backend API to be running.
- Sprint summary artifacts should drop into each `docs/sprints/<sprint>/` folder by default and reflect the frontend design language.
- Sprint perspectives should be exportable as PDF with embedded Dev Graph visuals, without requiring the UI to be open.
- Docker is required and should be fully operable from skills; an MCP server can be used for Docker operations.
- Outputs should be shareable: SVGs, MP4, GIF, and PDF.

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

Plan (detailed next steps)
1. Startup skills
   - Add explicit “mode prompts” for: docker-only, backend-only, full stack, and open page.
   - Detect docker availability and state; start only required containers.
   - Add lightweight health checks (API ready + port checks) and a final “ready summary.”
   - Align both Pixel Detective and Dev Graph scripts to the same flags and outputs.

2. Docker control + MCP
   - Define a docker capability map: list containers, start/stop/restart, logs, and ports.
   - If MCP is available, prefer it for controlled docker operations; fall back to shell.
   - Log docker actions taken (for reproducibility).

3. Sprint summary PDFs
   - Read `docs/sprints/` and generate one PDF per sprint folder by default.
   - Use frontend styles: typography, colors, and card spacing aligned to the UI theme.
   - Include “story cards” and a final “metrics/links” card per sprint.
   - Add optional cover page, and a minimal table of contents.

4. Sprint perspectives (PDF + visuals)
   - Produce a “perspectives” PDF that merges sprint narrative and Dev Graph visuals.
   - Pull visuals from the standalone exporter (SVG or rendered PNG).
   - Allow “per sprint window” exports tied to sprints.json.
   - Ensure output lives inside each sprint folder.

5. Dev Graph exports (cinematic + parity)
   - Provide a “cinematic” preset: slower relaxation, higher auto-fit padding, smooth zoom.
   - Add a “focus commit” preset for localized windows around a commit/hash.
   - Keep SVG as the source of truth; video/gif is derived from SVG frames only.

6. Documentation and packaging
   - Create a short quickstart in each SKILL.md (“best command to run”).
   - Add a top-level “skills index” section with common tasks and examples.
   - Plan for future npm packaging (folder structure + entry points).
