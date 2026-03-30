---
name: rituals-guide
description: "Audit and scaffold sprint documentation rituals based on MANIFESTO.md. Use when the user asks for sprint doc review, documentation audit, ritual scaffolding, sprint checklists, doc quality evaluation, or wants to follow the research -> spec -> prompt -> implement -> document workflow."
---

# Rituals Guide

Turn the lessons in `MANIFESTO.md` into a practical workflow: audit an existing sprint folder against the manifesto-derived rubric, then scaffold missing docs and templates to follow the same rituals consistently.

## Quickstart

```bash
# Audit a sprint and generate perspectives
python skills/rituals-guide/scripts/audit_and_scaffold_rituals.py --sprint sprint-11

# Audit and scaffold missing templates
python skills/rituals-guide/scripts/audit_and_scaffold_rituals.py --sprint sprint-11 --scaffold
```

## Workflow

1. **Audit** — Run the script with `--sprint <name>`. It checks the sprint folder against the rubric from [`MANIFESTO.md`](../../MANIFESTO.md) and [`manifesto-derived-rules.md`](../../docs/reference_guides/manifesto-derived-rules.md).
2. **Review** — Open the generated `RITUAL_AUDIT.md` and check which rituals passed or failed. Each finding links back to the manifesto rule it derives from.
3. **Scaffold** — Re-run with `--scaffold` to generate missing templates for failing rituals.
4. **Re-audit** — Run the audit again to confirm fixes. Repeat until all rituals pass.

## Outputs (per sprint folder)

| File | Generated when |
|------|---------------|
| `docs/sprints/<sprint>/RITUAL_AUDIT.md` | Always |
| `docs/sprints/<sprint>/PERSPECTIVES.md` | Always (calls sprint perspectives generator) |
| `docs/sprints/<sprint>/_linked_docs.json` | Always |
| `docs/sprints/<sprint>/RESEARCH_BRIEF.md` | `--scaffold` only |
| `docs/sprints/<sprint>/PROMPT_PACK.md` | `--scaffold` only |
| `docs/sprints/<sprint>/ACCEPTANCE_CHECKS.md` | `--scaffold` only |

## Error handling

- If the sprint folder does not exist under `docs/sprints/`, the script exits with an error. Create the folder first or check the sprint name.
- If `MANIFESTO.md` is missing at the repo root, the audit cannot run. Ensure the file is present.

## Notes

- Uses existing sprint docs as anchors; no new sprint metadata required.
- The audit rubric is derived from `MANIFESTO.md` and `docs/reference_guides/manifesto-derived-rules.md`.
