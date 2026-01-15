import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ANCHOR_HINTS = [
    "README.md",
    "PRD.md",
    "completion-summary",
    "SUMMARY",
    "mindmap",
    "technical-implementation-plan",
    "QUICK_REFERENCE",
]


@dataclass
class AuditResult:
    sprint_name: str
    sprint_dir: Path
    anchors_found: list[str]
    perspectives_generated: bool
    linked_docs_count: int
    rubric_score: int
    rubric_max: int
    notes: list[str]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


def discover_sprints(sprints_root: Path, include_nonstandard: bool) -> list[Path]:
    dirs = [p for p in sprints_root.iterdir() if p.is_dir()]
    if include_nonstandard:
        return sorted(dirs)
    filtered: list[Path] = []
    for p in dirs:
        name = p.name.lower()
        if name in {"planning", "templates"}:
            continue
        if name.startswith("sprint-") or name.startswith("s-") or name == "critical-ui-refactor":
            filtered.append(p)
    return sorted(filtered)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def clean_manifesto_line(line: str) -> str:
    value = line.rstrip("\n").replace("\ufffd", "")
    value = value.replace("\x1a", "+")  # SUB control char sometimes appears in mojibake
    value = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", value)
    value = value.replace("ƒ+'", "+")
    value = re.sub(r"ƒ\?[^\s]{0,12}", "", value)
    value = re.sub(r"\bdY[^\s]{0,16}", "", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"^(\s*#{1,6}\s*)\?+\s*", r"\1", value)
    value = re.sub(r"^\?+\s*", "", value)
    if value.count("**") % 2 == 1:
        value = re.sub(r"\*{2,}\s*$", "", value)
    value = re.sub(r"\s{2,}", " ", value).rstrip()
    return value


def ensure_perspectives(repo_root: Path, sprint_name: str) -> bool:
    script = repo_root / "skills" / "sprint-perspectives" / "scripts" / "generate_sprint_perspectives.py"
    if not script.exists():
        raise RuntimeError(
            "Missing sprint perspectives generator at skills/sprint-perspectives/scripts/generate_sprint_perspectives.py"
        )
    cmd = [sys.executable, str(script), "--sprint", sprint_name, "--no-pdf"]
    completed = run(cmd, cwd=repo_root)
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        return False
    return True


def scaffold_file(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return True


def load_linked_docs(sprint_dir: Path) -> list[dict[str, Any]]:
    p = sprint_dir / "_linked_docs.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def audit_rubric(sprint_dir: Path, linked_docs: list[dict[str, Any]]) -> tuple[int, int, list[str]]:
    score = 0
    max_score = 10
    notes: list[str] = []

    has_prd = (sprint_dir / "PRD.md").exists()
    has_readme = (sprint_dir / "README.md").exists()
    has_completion = bool(list(sprint_dir.glob("completion-summary*.md"))) or bool(
        list(sprint_dir.glob("COMPLETION_SUMMARY*.md"))
    )
    has_research_archive = (sprint_dir / "archive").exists()

    if has_readme:
        score += 2
    else:
        notes.append("Missing README.md (anchor narrative).")

    if has_prd:
        score += 2
    else:
        notes.append("Missing PRD.md (spec + success criteria).")

    if has_completion:
        score += 1
    else:
        notes.append("Missing completion summary (results + gaps).")

    if has_research_archive:
        score += 1
    else:
        notes.append("No archive/ folder (optional research pack).")

    if len(linked_docs) >= 5:
        score += 2
    elif len(linked_docs) > 0:
        score += 1
        notes.append("Linked evidence is present but thin; consider consolidating research notes.")
    else:
        notes.append("No linked evidence docs discovered via git co-updates.")

    if (sprint_dir / "PERSPECTIVES.md").exists():
        score += 1
    else:
        notes.append("PERSPECTIVES.md not found (run sprint perspectives generator).")

    if (sprint_dir / "PROMPT_PACK.md").exists():
        score += 1
    else:
        notes.append("PROMPT_PACK.md missing (recommended for repeatable prompting).")

    return score, max_score, notes


def extract_manifesto_excerpt(repo_root: Path) -> str:
    text = read_text(repo_root / "MANIFESTO.md")
    if not text:
        return ""
    marker = "The Formula That Emerged"
    idx = text.find(marker)
    if idx < 0:
        return ""
    snippet = text[idx : idx + 2200]
    lines = [clean_manifesto_line(l) for l in snippet.splitlines()[:60]]
    return "\n".join(lines).strip()


def extract_manifesto_outline(repo_root: Path) -> list[dict[str, Any]]:
    text = read_text(repo_root / "MANIFESTO.md")
    if not text:
        return []
    outline: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.startswith("#"):
            continue
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if not m:
            continue
        title = clean_manifesto_line(m.group(2).strip())
        if not title:
            continue
        outline.append({"level": len(m.group(1)), "title": title})
    return outline[:80]


def extract_manifesto_artifacts(repo_root: Path) -> list[str]:
    """
    Best-effort: list file-like paths referenced by MANIFESTO.md (docs/research artifacts).
    """
    text = read_text(repo_root / "MANIFESTO.md")
    if not text:
        return []

    artifacts: set[str] = set()

    # Inline code spans.
    parts = text.split("`")
    for token in parts[1::2]:
        value = token.strip().strip(".,;:")
        if not value:
            continue
        if value.endswith((".md", ".txt", ".pdf")):
            artifacts.add(value)
        if value.startswith(("docs/", "archive/", "exports/")):
            artifacts.add(value)

    # Markdown links: [label](path)
    for match in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        value = match.strip().strip(".,;:")
        if not value:
            continue
        if value.endswith((".md", ".txt", ".pdf")) or value.startswith(("docs/", "archive/", "exports/")):
            artifacts.add(value)

    # Bare paths.
    for line in text.splitlines():
        for prefix in ("docs/", "archive/", "exports/"):
            if prefix not in line:
                continue
            idx = line.find(prefix)
            cand = line[idx:].strip().strip("`").strip().strip(".,;:")
            if cand:
                artifacts.add(cand)

    cleaned: list[str] = []
    for a in sorted(artifacts):
        cleaned.append(a.replace("\\", "/"))
    return cleaned[:120]


def extract_rules_excerpt(repo_root: Path) -> str:
    path = repo_root / "docs" / "reference_guides" / "manifesto-derived-rules.md"
    text = read_text(path)
    if not text:
        return ""
    return "\n".join(text.splitlines()[:80])


def build_audit_md(
    sprint_name: str,
    anchors: list[str],
    linked_docs: list[dict[str, Any]],
    rubric_score: int,
    rubric_max: int,
    notes: list[str],
    manifesto_excerpt: str,
    manifesto_outline: list[dict[str, Any]],
    manifesto_artifacts: list[str],
    rules_excerpt: str,
) -> str:
    lines: list[str] = []
    lines.append(f"# Ritual Audit - {sprint_name}")
    lines.append("")
    lines.append("## Status")
    lines.append(f"- Rubric: {rubric_score} / {rubric_max}")
    lines.append(f"- Anchor docs found: {len(anchors)}")
    lines.append(f"- Linked evidence docs: {len(linked_docs)}")
    lines.append("")

    if notes:
        lines.append("## Notes")
        for n in notes:
            lines.append(f"- {n}")
        lines.append("")

    lines.append("## Anchor docs (inputs)")
    for a in anchors:
        lines.append(f"- {a}")
    lines.append("")

    lines.append("## Ritual loop (how to work this repo)")
    lines.append("- Research: collect notes, constraints, alternatives, and metrics.")
    lines.append("- Spec: PRD + acceptance checks that can be verified from logs/files/UI.")
    lines.append("- Prompt: keep a prompt pack with definitions + constraints + one real example.")
    lines.append("- Implement: ship the smallest reversible slice, then iterate.")
    lines.append("- Document: update sprint anchors and generate perspectives (story + receipts).")
    lines.append("")

    lines.append("## Linked evidence (top)")
    for item in linked_docs[:12]:
        path = item.get("path", "")
        count = item.get("cochange_count", 0)
        title = item.get("title", "")
        tags = item.get("tags") or []
        lines.append(f"- `{path}` (co-changed {count}x)")
        if title:
            lines.append(f"  - Title: {title}")
        if tags:
            lines.append(f"  - Tags: {', '.join(tags)}")
    lines.append("")

    lines.append("## Rituals (excerpt from MANIFESTO.md)")
    lines.append(manifesto_excerpt.strip() or "_(No excerpt extracted)_")
    lines.append("")

    lines.append("## Manifesto outline (headings)")
    if manifesto_outline:
        for h in manifesto_outline[:50]:
            indent = "  " * max(0, int(h.get("level", 1)) - 1)
            title = str(h.get("title", "")).strip()
            if title:
                lines.append(f"- {indent}{title}")
    else:
        lines.append("_(No outline extracted)_")
    lines.append("")

    lines.append("## Manifesto referenced artifacts (best-effort)")
    if manifesto_artifacts:
        for a in manifesto_artifacts:
            lines.append(f"- `{a}`")
    else:
        lines.append("_(No artifacts extracted)_")
    lines.append("")

    lines.append("## Prompting rules (from manifesto-derived guide)")
    lines.append(rules_excerpt.strip() or "_(No excerpt extracted)_")
    lines.append("")

    lines.append("## Recommended next actions")
    lines.append("- Ensure PRD contains explicit acceptance checks (3-7 bullets).")
    lines.append("- Add/keep a RESEARCH_BRIEF that lists alternatives + constraints + metrics.")
    lines.append("- Keep a PROMPT_PACK with: goal, definitions, constraints, example payload/log, acceptance checklist.")
    lines.append("- Run sprint perspectives again after adding research notes to refresh linked evidence.")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and scaffold sprint rituals based on the Manifesto")
    parser.add_argument("--sprint", help="Sprint folder name (e.g., sprint-11)")
    parser.add_argument("--all", action="store_true", help="Process all sprint folders")
    parser.add_argument("--include-nonstandard", action="store_true")
    parser.add_argument("--scaffold", action="store_true", help="Create missing ritual template files")
    args = parser.parse_args()

    repo_root = repo_root_from_here()
    sprints_root = repo_root / "docs" / "sprints"
    if not sprints_root.exists():
        print("docs/sprints not found; run from repo context.", file=sys.stderr)
        return 2

    if not args.sprint and not args.all:
        args.all = True

    if args.sprint:
        targets = [sprints_root / args.sprint]
    else:
        targets = discover_sprints(sprints_root, include_nonstandard=args.include_nonstandard)

    manifesto_excerpt = extract_manifesto_excerpt(repo_root)
    manifesto_outline = extract_manifesto_outline(repo_root)
    manifesto_artifacts = extract_manifesto_artifacts(repo_root)
    rules_excerpt = extract_rules_excerpt(repo_root)

    for sprint_dir in targets:
        if not sprint_dir.exists():
            print("Missing sprint folder:", sprint_dir, file=sys.stderr)
            continue

        sprint_name = sprint_dir.name
        anchors: list[str] = []
        for hint in ANCHOR_HINTS:
            for p in sprint_dir.glob(f"*{hint}*"):
                if p.is_file():
                    anchors.append(p.name)
        anchors = sorted(set(anchors))

        perspectives_ok = ensure_perspectives(repo_root, sprint_name)
        linked_docs = load_linked_docs(sprint_dir)

        rubric_score, rubric_max, notes = audit_rubric(sprint_dir, linked_docs)
        audit_text = build_audit_md(
            sprint_name=sprint_name,
            anchors=anchors,
            linked_docs=linked_docs,
            rubric_score=rubric_score,
            rubric_max=rubric_max,
            notes=notes,
            manifesto_excerpt=manifesto_excerpt,
            manifesto_outline=manifesto_outline,
            manifesto_artifacts=manifesto_artifacts,
            rules_excerpt=rules_excerpt,
        )
        (sprint_dir / "RITUAL_AUDIT.md").write_text(audit_text, encoding="utf-8")

        if args.scaffold:
            scaffold_file(
                sprint_dir / "RESEARCH_BRIEF.md",
                """# Research Brief

## Hypothesis
- <what do we believe will help?>

## Alternatives (2-3)
- Option A: <trade-offs>
- Option B: <trade-offs>

## Constraints
- <device / GPU / memory / time / ports>

## Metrics
- <how we'll judge success (numbers)>

## Plan
- <small experiment with low blast radius>
""",
            )
            scaffold_file(
                sprint_dir / "ACCEPTANCE_CHECKS.md",
                """# Acceptance Checks

- [ ] <check 1>
- [ ] <check 2>
- [ ] <check 3>
""",
            )
            scaffold_file(
                sprint_dir / "PROMPT_PACK.md",
                """# Prompt Pack

## Goal (observable)
<what "good" looks like on screen / in logs / in files>

## Scope
- Affected folders/services/pages:
- Out of scope:

## Definitions
- <term>: <meaning>

## Constraints
- OS:
- Ports:
- GPU/CPU:
- Memory/time budget:

## Evidence (one real example)
- Payload/log/screenshot:

## Acceptance
- [ ] <check 1>
- [ ] <check 2>
- [ ] <check 3>

## Pointers
- Relevant files/paths:
- Known failure points:
""",
            )

        status = "ok" if perspectives_ok else "partial"
        print(f"Ritual audit generated for {sprint_name} ({status})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
