# Skills (local)

This folder contains local Codex skill definitions (`*/SKILL.md`) plus helper scripts under `*/scripts/` used by Pixel Detective and Dev Graph.

## Quickstart (common commands)
- Start Pixel Detective: `powershell -ExecutionPolicy Bypass -File skills\\start-pixel-detective\\scripts\\start_pixel_detective.ps1 -Mode full -Open`
- Start Dev Graph: `powershell -ExecutionPolicy Bypass -File skills\\start-dev-graph\\scripts\\start_dev_graph.ps1 -Mode full -Open`
- Docker inventory/actions: `powershell -ExecutionPolicy Bypass -File skills\\docker-helper\\scripts\\docker_inventory.ps1 -Action status -ListCapabilities`
- Pixel Detective exports: `python skills\\pixel-detective-exports\\scripts\\export_umap_hdbscan.py --collection <name>`
- Dev Graph API-only timeline exports: `node skills\\dev-graph-exports\\scripts\\export_timeline_segments_svg_parity.js --api http://localhost:8080`
- Sprint summary PDFs (defaults to all sprints): `python skills\\sprint-summary-pdf\\scripts\\generate_sprint_summary_pdf.py`
- Sprint perspectives (git-driven, per sprint): `python skills\\sprint-perspectives\\scripts\\generate_sprint_perspectives.py --sprint sprint-11 --no-pdf`
- Rituals audit + scaffold: `python skills\\rituals-guide\\scripts\\audit_and_scaffold_rituals.py --sprint sprint-11 --scaffold`

## Skill types (minimum 3)
This repo is built around 3 reusable skill types:
1) **Dev Graph** (exports + manipulation): `dev-graph-exports`, `start-dev-graph`
2) **Pixel Detective** (exports + collection ops): `pixel-detective-exports`, `start-pixel-detective`
3) **Sprint perspectives** (story + evidence cards): `sprint-perspectives` (generator) + `rituals-guide` (audit/scaffold)

## Source-of-truth scope (implemented)
- `start-pixel-detective`: modes `full|backend|services|frontend|status|stop`, plus `-Open` + optional `-Page`.
- `start-dev-graph`: modes `full|backend|services|frontend|status|stop`, plus `-Open` + optional `-Page`.
- `docker-helper`: Docker inventory, repo-root-aware `docker compose` actions (`start|stop|restart|logs`).
- `pixel-detective-exports`: UMAP projection export + clustering (GPU UMAP service), plus collection operations via ingestion API.
- `dev-graph-exports`: API-only SVG-parity timeline exporter (Node.js) plus optional UI-driven Playwright scripts.
- `sprint-summary-pdf`: per-sprint HTML/PDF card summaries from `docs/sprints/*` saved into each sprint folder.
- `sprint-perspectives`: per-sprint `PERSPECTIVES.md` + cards, derived from sprint anchor docs + git co-updated evidence and churn metrics.
- `rituals-guide`: per-sprint ritual audit + optional scaffolding templates, derived from `MANIFESTO.md`.

## Notes and dependencies
- `dev-graph-exports` API-only exporter requires Node.js 18+ (global `fetch`).
- `sprint-summary-pdf` and `sprint-perspectives` produce PDFs when `weasyprint` is installed; otherwise they write HTML next to the intended PDF path.
- `pixel-detective-exports` report PDF generation prefers `weasyprint` and falls back to `playwright` if available; otherwise it leaves HTML.

## Validation (before installing system-wide)
- Run: `powershell -ExecutionPolicy Bypass -File skills\\validate_skills.ps1`
- Optional: `-SkipPython` or `-SkipNode` (if those runtimes are not installed on the target machine)

## Tasklist (backlog and next improvements)
- [x] Start scripts for Pixel Detective and Dev Graph with consistent flags and ready summaries
- [x] Docker capability mapping (MCP fallback still pending)
- [x] Health checks for API readiness and basic port verification
- [x] Pixel Detective export skill (standalone, UI-independent)
- [x] Sprint perspectives (git-driven narrative + evidence cards; no Dev Graph required)
- [x] Rituals audit + scaffold (manifesto-derived rubric + templates)
- [ ] Improve sprint perspectives story quality (manifesto-style beats; fewer bullets, more narrative)
- [ ] Tag and surface evidence docs more deeply (titles/headings, doc types, "research helped build X")
- [ ] Add optional Dev Graph enrichment (when running) for deeper code-change attribution and sprint-window presets
- [ ] Update sprint-summary-pdf template to fully match Pixel Detective typography and color tokens
- [ ] Add sprint perspectives PDFs with embedded Dev Graph visuals (SVG/PNG receipts)
- [ ] Add MCP-based Docker control fallback (scripts currently use Docker CLI directly)

