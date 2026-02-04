---
name: sprint-summary-pdf
description: Generate per-sprint PDF summaries with a card layout from docs/sprints. Use when the user asks for sprint summaries, sprint recap PDFs, shareable sprint story cards, or to drop PDFs into each sprint folder.
---

# Sprint Summary PDF

Use this skill to generate a clean PDF per sprint, saved inside each sprint folder.

## Quickstart
- All sprints (default): `python skills/sprint-summary-pdf/scripts/generate_sprint_summary_pdf.py`
- Single sprint: `python skills/sprint-summary-pdf/scripts/generate_sprint_summary_pdf.py --sprint sprint-11`

## Inputs
- `docs/sprints/*/README.md`
- `docs/sprints/*/PRD.md`
- `docs/sprints/*/*SUMMARY*.md`
- `docs/sprints/*/completion-summary*.md`
- `docs/sprints/*/mindmap*.md`

## Output
- Default filename: `SPRINT_SUMMARY_CARDS.pdf`
- Save inside each sprint folder, for example:
  - `docs/sprints/sprint-11/SPRINT_SUMMARY_CARDS.pdf`

## Content extraction
For each sprint folder, extract:
- Title and sprint name
- Dates or time window (if present)
- Goal or theme (from README or PRD)
- Key wins or delivered features
- Risks or known gaps
- Next steps or transition notes
- Metrics or performance highlights (if present)

If a sprint is missing a summary file, synthesize a short summary from README and PRD only.

## Layout and style
- Use a grid of cards (4 to 6 cards per sprint).
- Visual tone inspired by the Pixel Detective frontend:
  - dark base, high contrast text
  - cyan or teal accent lines
  - rounded cards, subtle shadows
  - bold section headers
- Keep it readable at a glance. Each card should be 3 to 6 bullets.
- Include a small header with sprint name, status, and dates.

## PDF generation approach
- Build a single HTML per sprint with inline CSS.
- Render to PDF using WeasyPrint when available; otherwise leave HTML for manual export.
- Do not depend on running services.

## Scope control
- If user asks for a single sprint, only generate that sprint PDF.
- If user asks for all, iterate every sprint folder under `docs/sprints/`.

## Template and script
- Template: `skills/sprint-summary-pdf/assets/sprint_cards_template.html`
- Script: `python skills/sprint-summary-pdf/scripts/generate_sprint_summary_pdf.py` (defaults to `--all`)
- Single sprint: `--sprint sprint-11`

## Notes
- If a sprint folder has no bullet lists, generate a single Summary card using the first paragraph of README/PRD.
- Prefer README for narrative, PRD for goals, and completion summaries for wins and gaps.
- Keep cards concise; trim long bullets and drop low-signal items.
