---
name: sprint-summary-pdf
description: "Generate per-sprint PDF summaries with a card layout from docs/sprints. Use when the user asks for sprint summaries, sprint recap PDFs, shareable sprint story cards, print-ready sprint reports, or to drop PDFs into each sprint folder."
---

# Sprint Summary PDF

Generate a clean, card-layout PDF per sprint saved inside each sprint folder.

## Quickstart

```bash
# All sprints
python skills/sprint-summary-pdf/scripts/generate_sprint_summary_pdf.py

# Single sprint
python skills/sprint-summary-pdf/scripts/generate_sprint_summary_pdf.py --sprint sprint-11
```

## Workflow

1. **Run the script** targeting one sprint or all sprints.
2. **Verify output** — Confirm the PDF exists in the sprint folder:
   ```bash
   ls docs/sprints/sprint-11/SPRINT_SUMMARY_CARDS.pdf
   ```
3. **Review** — Open the PDF and check that cards render correctly with the expected content.

## Inputs

Each sprint folder is scanned for:
- `docs/sprints/*/README.md`
- `docs/sprints/*/PRD.md`
- `docs/sprints/*/*SUMMARY*.md` / `completion-summary*.md`
- `docs/sprints/*/mindmap*.md`

## Output

- Filename: `SPRINT_SUMMARY_CARDS.pdf` inside each sprint folder (e.g. `docs/sprints/sprint-11/SPRINT_SUMMARY_CARDS.pdf`).

## Content extraction

For each sprint, the script extracts: title, dates/time window, goal/theme (from README or PRD), key wins, risks/gaps, next steps, and metrics. If a sprint lacks a summary file, a short summary is synthesized from README and PRD.

## Layout and style

- Grid of 4–6 cards per sprint, each card 3–6 bullets.
- Dark base with high-contrast text, cyan/teal accent lines, rounded cards, subtle shadows.
- Template: [`assets/sprint_cards_template.html`](assets/sprint_cards_template.html).

## PDF generation

- Builds a single HTML per sprint with inline CSS, then renders via WeasyPrint.
- If WeasyPrint is not installed (`pip install weasyprint`), the HTML is left for manual export.
- Does not depend on running services.

## Error handling

- If WeasyPrint is missing, the script generates HTML only and logs a warning. Install with `pip install weasyprint`.
- If a sprint folder contains no recognizable docs, that sprint is skipped with a warning.

## Notes

- Prefer README for narrative, PRD for goals, completion summaries for wins and gaps.
- Keep cards concise; long bullets are trimmed and low-signal items dropped.
