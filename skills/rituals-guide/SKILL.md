---
name: rituals-guide
description: Audit and scaffold sprint documentation rituals based on MANIFESTO.md. Use when the user wants to follow the research -> spec -> prompt -> implement -> document workflow, generate checklists/templates, or evaluate documentation quality for a sprint.
---

# Rituals Guide

This skill turns the lessons in `MANIFESTO.md` into a practical workflow:
1) audit an existing sprint folder and its linked evidence, then
2) scaffold missing docs/templates to follow the same rituals consistently.

## Quickstart
- Audit + generate perspectives: `python skills/rituals-guide/scripts/audit_and_scaffold_rituals.py --sprint sprint-11`
- Audit + scaffold missing templates: `python skills/rituals-guide/scripts/audit_and_scaffold_rituals.py --sprint sprint-11 --scaffold`

## Outputs (per sprint folder)
- `docs/sprints/<sprint>/RITUAL_AUDIT.md`
- (Calls sprint perspectives generator) `docs/sprints/<sprint>/PERSPECTIVES.md` + `docs/sprints/<sprint>/_linked_docs.json`
- Optional scaffolds (only when `--scaffold`):
  - `docs/sprints/<sprint>/RESEARCH_BRIEF.md`
  - `docs/sprints/<sprint>/PROMPT_PACK.md`
  - `docs/sprints/<sprint>/ACCEPTANCE_CHECKS.md`

## Notes
- Uses existing sprint docs as anchors; no new sprint metadata required.
- The audit rubric is derived from `MANIFESTO.md` and `docs/reference_guides/manifesto-derived-rules.md`.

