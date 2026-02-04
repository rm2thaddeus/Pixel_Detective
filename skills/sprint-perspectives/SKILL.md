---
name: sprint-perspectives
description: Generate per-sprint perspectives (narrative + cards) by mining git history for documents and files co-updated alongside sprint anchor docs. Use when the user asks for sprint perspectives, evidence linking, research doc discovery, or sprint retrospectives with code-change metrics.
---

# Sprint Perspectives

Generate a per-sprint `PERSPECTIVES.md` plus a card-style HTML/PDF report by:
1) summarizing sprint anchor docs inside `docs/sprints/<sprint>/`, and
2) using git history to discover which other docs/files were co-updated while those sprint docs were edited.

## Quickstart
- Single sprint: `python skills/sprint-perspectives/scripts/generate_sprint_perspectives.py --sprint sprint-11 --no-pdf`
- All sprints: `python skills/sprint-perspectives/scripts/generate_sprint_perspectives.py --all --no-pdf`

## Optional Dev Graph (enrichment + visuals)
- Add window/subgraph receipts (requires Dev Graph API): `python skills/sprint-perspectives/scripts/generate_sprint_perspectives.py --sprint sprint-11 --dev-graph-api http://localhost:8080 --no-pdf`
- Embed visuals (drop SVG/PNG into the sprint folder first):
  - Put files under: `docs/sprints/sprint-11/_dev_graph_visuals/`
  - Then run: `python skills/sprint-perspectives/scripts/generate_sprint_perspectives.py --sprint sprint-11 --no-pdf`

## Outputs (per sprint folder)
- `docs/sprints/<sprint>/PERSPECTIVES.md`
- `docs/sprints/<sprint>/_linked_docs.json` (docs only)
- `docs/sprints/<sprint>/_cochanged_files.json` (all files)
- `docs/sprints/<sprint>/SPRINT_PERSPECTIVES_CARDS.pdf` (when `weasyprint` is installed; otherwise HTML is left next to the intended PDF path)

## Notes
- Works git-first (no Dev Graph required). When provided, `--dev-graph-api` adds sprint-window receipts and basic subgraph counts.
- The main protagonist is documentation evidence (`.md/.txt/.pdf`), but code-change metrics are included as supportive context.
