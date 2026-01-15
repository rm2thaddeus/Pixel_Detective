import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen


TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "perspectives_cards_template.html"

DEFAULT_MD_NAME = "PERSPECTIVES.md"
DEFAULT_JSON_NAME = "_linked_docs.json"
DEFAULT_ALL_FILES_JSON_NAME = "_cochanged_files.json"
DEFAULT_PDF_NAME = "SPRINT_PERSPECTIVES_CARDS.pdf"
DEFAULT_DEV_GRAPH_VISUALS_DIR = "_dev_graph_visuals"

VISUAL_EXTS = {".svg", ".png", ".jpg", ".jpeg"}

ANCHOR_PATTERNS = [
    "README.md",
    "PRD.md",
    "*SUMMARY*.md",
    "completion-summary*.md",
    "COMPLETION_SUMMARY*.md",
    "mindmap*.md",
    "*MINDMAP*.md",
    "technical-implementation-plan*.md",
    "TECHNICAL-IMPLEMENTATION-PLAN*.md",
    "QUICK_REFERENCE*.md",
    "quick_reference*.md",
    "TASK_BREAKDOWN*.md",
    "BACKLOG*.md",
]

DOC_EXTS = {".md", ".txt", ".pdf"}

LANG_BY_EXT = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ps1": "PowerShell",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".toml": "TOML",
    ".md": "Docs (Markdown)",
    ".txt": "Docs (Text)",
    ".pdf": "Docs (PDF)",
    ".css": "CSS",
    ".scss": "CSS",
    ".html": "HTML",
    ".sql": "SQL",
}


@dataclass
class Candidate:
    path: str
    cochange_count: int = 0
    last_commit: str = ""
    last_commit_ts: int = 0
    statuses: set[str] = field(default_factory=set)
    commits: list[str] = field(default_factory=list)

    def bump(self, commit: str, commit_ts: int, status: str) -> None:
        self.cochange_count += 1
        self.statuses.add(status)
        if commit_ts >= self.last_commit_ts:
            self.last_commit = commit
            self.last_commit_ts = commit_ts
        if len(self.commits) < 20:
            self.commits.append(commit)


@dataclass
class Churn:
    added: int = 0
    deleted: int = 0

    @property
    def total(self) -> int:
        return self.added + self.deleted


@dataclass
class MdSection:
    level: int
    title: str
    lines: list[str]


def run_git(repo_root: Path, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git is required but was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git command failed: git {' '.join(args)}\n{exc.stderr}") from exc
    return completed.stdout


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def fetch_json(url: str) -> Any:
    with urlopen(url) as response:
        payload = response.read().decode("utf-8", errors="replace")
        return json.loads(payload)


def parse_sprint_number(sprint_name: str) -> Optional[str]:
    m = re.search(r"(\d+)", sprint_name)
    if not m:
        return None
    try:
        return str(int(m.group(1)))
    except ValueError:
        return None


def discover_dev_graph_visuals(sprint_dir: Path, dir_name: str) -> list[str]:
    visuals_dir = sprint_dir / dir_name
    if not visuals_dir.exists() or not visuals_dir.is_dir():
        return []
    found: list[str] = []
    for p in sorted(visuals_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in VISUAL_EXTS:
            found.append(p.relative_to(sprint_dir).as_posix())
    return found


def enrich_from_dev_graph(dev_graph_api: str, sprint_number: str) -> Optional[dict[str, Any]]:
    api = dev_graph_api.rstrip("/")
    try:
        meta = fetch_json(f"{api}/api/v1/dev-graph/sprints/{quote(sprint_number)}")
        if not isinstance(meta, dict) or meta.get("error"):
            return None
    except (URLError, ValueError):
        return None

    start_date = meta.get("start_date") or meta.get("start")
    end_date = meta.get("end_date") or meta.get("end")
    if start_date and end_date:
        try:
            mapped = fetch_json(
                f"{api}/api/v1/dev-graph/sprint/map?number={quote(sprint_number)}&start_date={quote(str(start_date))}&end_date={quote(str(end_date))}"
            )
            if isinstance(mapped, dict):
                metrics = mapped.get("metrics") or {}
                if isinstance(metrics, dict) and "count" in metrics:
                    meta["commit_count_in_window"] = metrics.get("count")
        except (URLError, ValueError):
            pass

    try:
        subgraph = fetch_json(f"{api}/api/v1/dev-graph/sprints/{quote(sprint_number)}/subgraph")
        if isinstance(subgraph, dict):
            nodes = subgraph.get("nodes") or []
            edges = subgraph.get("edges") or []
            meta["subgraph_node_count"] = len(nodes) if isinstance(nodes, list) else 0
            meta["subgraph_edge_count"] = len(edges) if isinstance(edges, list) else 0
    except (URLError, ValueError):
        pass

    return meta


def clean_line(line: str) -> str:
    value = line.strip()
    if not value:
        return ""

    value = value.replace("\u00ad", "").replace("\u200b", "").replace("\ufffd", "")
    value = value.replace("**", "").replace("__", "")
    value = re.sub(r"\s{2,}", " ", value)

    # Avoid console mojibake: drop non-ASCII (emoji, badges) in generated artifacts.
    value = value.encode("ascii", "ignore").decode("ascii")

    value = re.sub(r"\bdY[^\s]{0,16}", "", value)
    # Replace-markers sometimes render as '?' in some environments; drop them when used as standalone tokens.
    value = re.sub(r"(?:^|\s)\?\.(?=\s|$)", " ", value)
    value = re.sub(r"(?:^|\s)\?(?=\s|$)", " ", value)
    value = re.sub(r"(?:^|\s)[^\x00-\x7F]{1,6}\.(?=\s)", " ", value)
    value = re.sub(r"(?:^|\s)\.(?=\s)", " ", value)
    value = re.sub(r"^\s*[^A-Za-z0-9\[\(\*`]+", "", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip()


def extract_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*[-*]\s+", line):
            bullets.append(clean_line(re.sub(r"^\s*[-*]\s+", "", line).strip()))
    return [b for b in bullets if b]


def markdown_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("#"):
            value = clean_line(line.lstrip("#").strip())
            if value:
                return value
    for line in text.splitlines():
        value = clean_line(line.strip())
        if value:
            return value[:80]
    return fallback


def parse_markdown_sections(text: str) -> list[MdSection]:
    sections: list[MdSection] = []
    current = MdSection(level=0, title="", lines=[])
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            if current.lines or current.title:
                sections.append(current)
            current = MdSection(level=len(m.group(1)), title=clean_line(m.group(2)), lines=[])
            continue
        current.lines.append(line.rstrip())
    if current.lines or current.title:
        sections.append(current)
    return sections


def find_section(sections: list[MdSection], title_contains: str) -> Optional[MdSection]:
    needle = title_contains.lower()
    for s in sections:
        if needle in s.title.lower():
            return s
    return None


def find_section_exact(sections: list[MdSection], title_exact: str) -> Optional[MdSection]:
    needle = clean_line(title_exact).lower()
    for s in sections:
        if s.title.lower() == needle:
            return s
    return None


def collect_child_section_titles(sections: list[MdSection], parent_title_contains: str, max_items: int) -> list[str]:
    parent = find_section(sections, parent_title_contains)
    if not parent:
        return []
    try:
        idx = sections.index(parent)
    except ValueError:
        return []
    out: list[str] = []
    parent_level = parent.level
    for s in sections[idx + 1 :]:
        if s.level <= parent_level:
            break
        if s.title:
            out.append(clean_line(s.title))
        if len(out) >= max_items:
            break
    return [o for o in out if o]


def limit(items: list[str], max_items: int) -> list[str]:
    return items[:max_items]


def section_bullets(section: Optional[MdSection], max_items: int) -> list[str]:
    if not section:
        return []
    return limit([b for b in extract_bullets("\n".join(section.lines)) if b], max_items)


def truncate_sentence(text: str, max_chars: int) -> str:
    t = clean_line(text)
    if len(t) <= max_chars:
        return t
    cut = t[:max_chars]
    for sep in [". ", "; ", " - ", ", "]:
        idx = cut.rfind(sep)
        if idx > 80:
            base = cut[: idx + 1].rstrip().rstrip(".")
            return base + "..."
    base = cut.rstrip().rstrip(".")
    return base + "..."


def discover_sprint_dirs(sprints_root: Path, include_nonstandard: bool) -> list[Path]:
    all_dirs = [p for p in sprints_root.iterdir() if p.is_dir()]
    if include_nonstandard:
        return sorted(all_dirs)
    allowed = []
    for p in all_dirs:
        name = p.name.lower()
        if name in {"planning", "templates"}:
            continue
        if name.startswith("sprint-") or name.startswith("s-") or name == "critical-ui-refactor":
            allowed.append(p)
    return sorted(allowed)


def find_anchor_files(sprint_dir: Path) -> list[Path]:
    found: list[Path] = []
    for pattern in ANCHOR_PATTERNS:
        found.extend(sorted(sprint_dir.glob(pattern)))
    seen = set()
    anchors = []
    for p in found:
        if p.is_file() and p.name not in seen:
            seen.add(p.name)
            anchors.append(p)
    return anchors


def git_commit_ts(repo_root: Path, commit: str) -> int:
    out = run_git(repo_root, ["show", "-s", "--format=%ct", commit]).strip()
    try:
        return int(out)
    except ValueError:
        return 0


def collect_anchor_commits(repo_root: Path, rel_paths: list[str]) -> dict[str, int]:
    commits: dict[str, int] = {}
    for rel in rel_paths:
        out = run_git(repo_root, ["log", "--follow", "--format=%H", "--", rel])
        for line in out.splitlines():
            h = line.strip()
            if h and h not in commits:
                commits[h] = 0
    for h in list(commits.keys()):
        commits[h] = git_commit_ts(repo_root, h)
    return commits


def parse_name_status(output: str) -> list[tuple[str, Optional[str], str]]:
    changes: list[tuple[str, Optional[str], str]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        if status.startswith(("R", "C")):
            if len(parts) >= 3:
                changes.append((status, parts[1], parts[2]))
        else:
            changes.append((status, None, parts[1]))
    return changes


def collect_cochanged_candidates(
    repo_root: Path,
    anchor_paths: set[str],
    commit_ts: dict[str, int],
) -> dict[str, Candidate]:
    candidates: dict[str, Candidate] = {}
    for commit, ts in commit_ts.items():
        out = run_git(repo_root, ["show", "--name-status", "-M", "--format=", commit])
        for status, old, new in parse_name_status(out):
            if new in anchor_paths or (old and old in anchor_paths):
                continue
            cand = candidates.get(new)
            if not cand:
                cand = Candidate(path=new)
                candidates[new] = cand
            cand.bump(commit=commit, commit_ts=ts, status=status)
    return candidates


def normalize_git_numstat_path(raw: str) -> str:
    path = raw.strip()
    if "=>" in path:
        path = path.replace("{", "").replace("}", "")
        path = path.split("=>")[-1].strip()
    return path


def classify_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in LANG_BY_EXT:
        return LANG_BY_EXT[ext]
    if ext:
        return ext.lstrip(".").upper()
    return "Other"


def collect_churn(repo_root: Path, commits: Iterable[str]) -> tuple[dict[str, Churn], dict[str, Churn]]:
    churn_by_path: dict[str, Churn] = {}
    churn_by_lang: dict[str, Churn] = {}
    for commit in commits:
        out = run_git(repo_root, ["show", "--numstat", "--format=", commit])
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            a_raw, d_raw, p_raw = parts[0], parts[1], parts[2]
            if a_raw == "-" or d_raw == "-":
                continue
            try:
                added = int(a_raw)
                deleted = int(d_raw)
            except ValueError:
                continue
            path = normalize_git_numstat_path(p_raw)
            churn_by_path.setdefault(path, Churn()).added += added
            churn_by_path.setdefault(path, Churn()).deleted += deleted
            lang = classify_language(path)
            churn_by_lang.setdefault(lang, Churn()).added += added
            churn_by_lang.setdefault(lang, Churn()).deleted += deleted
    return churn_by_path, churn_by_lang


def is_doc(path: str) -> bool:
    return Path(path).suffix.lower() in DOC_EXTS


def doc_excerpt(repo_root: Path, path: str) -> dict[str, Any]:
    p = repo_root / path
    ext = p.suffix.lower()
    info: dict[str, Any] = {"title": "", "headings": []}
    if not p.exists():
        return info
    if ext in {".md", ".txt"}:
        text = safe_read_text(p)
        info["title"] = markdown_title(text, fallback=p.name)
        headings = []
        for line in text.splitlines():
            if line.startswith("#"):
                headings.append(clean_line(line.lstrip("#").strip()))
        info["headings"] = [h for h in headings if h][:8]
    return info


def score_and_rank(candidates: dict[str, Candidate]) -> list[Candidate]:
    return sorted(candidates.values(), key=lambda c: (c.cochange_count, c.last_commit_ts), reverse=True)


def escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def render_chip(label: str, value: str, accent: str) -> str:
    return (
        f'<span class="chip chip-{escape_html(accent)}">'
        f'<span class="chip-label">{escape_html(label)}</span>'
        f'<span class="chip-value">{escape_html(value)}</span>'
        "</span>"
    )


def render_bar_rows(items: list[tuple[str, int]], max_total: int) -> str:
    rows = []
    for name, total in items:
        pct = 0 if max_total <= 0 else int((total / max_total) * 100)
        rows.append(
            '<div class="bar-row">'
            f'<div class="bar-label">{escape_html(name)}</div>'
            '<div class="bar-track">'
            f'<div class="bar-fill" style="width:{pct}%"></div>'
            "</div>"
            f'<div class="bar-value">{escape_html(str(total))}</div>'
            "</div>"
        )
    return "".join(rows)


def render_hotspots_table(rows: list[tuple[str, Churn]]) -> str:
    body = []
    for path, churn in rows:
        body.append(
            "<tr>"
            f"<td class=\"mono\">{escape_html(path)}</td>"
            f"<td class=\"num\">+{churn.added}</td>"
            f"<td class=\"num\">-{churn.deleted}</td>"
            f"<td class=\"num\">{churn.total}</td>"
            "</tr>"
        )
    return (
        "<table class=\"table\">"
        "<thead><tr><th>File</th><th>+Lines</th><th>-Lines</th><th>Churn</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table>"
    )


def render_html(title: str, subtitle: str, meta: str, cards_html: str, footer_left: str) -> str:
    template = safe_read_text(TEMPLATE_PATH)
    return (
        template.replace("{{TITLE}}", escape_html(title))
        .replace("{{SUBTITLE}}", escape_html(subtitle))
        .replace("{{META}}", escape_html(meta))
        .replace("{{CARDS}}", cards_html)
        .replace("{{FOOTER_LEFT}}", escape_html(footer_left))
    )


def try_write_pdf(html: str, output_pdf: Path, keep_html: bool) -> bool:
    html_path = output_pdf.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    try:
        from weasyprint import HTML  # type: ignore
    except Exception:
        return False

    HTML(string=html, base_url=str(output_pdf.parent)).write_pdf(str(output_pdf))
    if not keep_html:
        html_path.unlink(missing_ok=True)
    return True


def card(title: str, inner_html: str, span2: bool = False) -> str:
    cls = "card span2" if span2 else "card"
    return f'<div class="{cls}"><h3>{escape_html(title)}</h3>{inner_html}</div>'


def tag_doc(path: str, title: str) -> list[str]:
    tags: list[str] = []
    lower = (path + " " + title).lower()
    if any(k in lower for k in ["research", "guide", "reference", "analysis"]):
        tags.append("evidence")
    if any(k in lower for k in ["plan", "roadmap", "implementation"]):
        tags.append("plan")
    if any(k in lower for k in ["metric", "performance", "benchmark", "latency", "throughput"]):
        tags.append("metrics")
    if "docs/reference_guides" in lower:
        tags.append("reference")
    if "docs/sprints" in lower:
        tags.append("sprint")
    if "manifesto" in lower:
        tags.append("ritual")
    if path.lower().endswith(".pdf"):
        tags.append("pdf")
    return sorted(set(tags))


def build_cards_html(
    story_blurb: str,
    cold_open_points: list[str],
    shipped_map: dict[str, list[str]],
    evidence_items: list[dict[str, Any]],
    churn_by_lang: dict[str, Churn],
    churn_by_path: dict[str, Churn],
    next_scene: list[str],
    performance_receipts: list[str],
    commit_count: int,
    dev_graph_meta: Optional[dict[str, Any]] = None,
    dev_graph_visuals: Optional[list[str]] = None,
) -> str:
    total_added = sum(v.added for v in churn_by_lang.values())
    total_deleted = sum(v.deleted for v in churn_by_lang.values())

    chips = [
        render_chip("Commits", str(commit_count), accent="cyan"),
        render_chip("Evidence Docs", str(len(evidence_items)), accent="aqua"),
        render_chip("Churn", f"+{total_added} / -{total_deleted}", accent="teal"),
    ]
    if dev_graph_meta:
        dg_commits = dev_graph_meta.get("commit_count_in_window")
        if dg_commits is not None:
            chips.append(render_chip("Dev Graph", f"{dg_commits} commits", accent="cyan"))
        sg_nodes = dev_graph_meta.get("subgraph_node_count")
        sg_edges = dev_graph_meta.get("subgraph_edge_count")
        if sg_nodes is not None and sg_edges is not None:
            chips.append(render_chip("Sprint Subgraph", f"{sg_nodes}n/{sg_edges}e", accent="aqua"))

    top_langs = sorted(churn_by_lang.items(), key=lambda kv: kv[1].total, reverse=True)[:6]
    totals = [(lang, churn.total) for lang, churn in top_langs]
    max_total = max([t for _, t in totals], default=0)

    receipts_html = (
        f'<div class="chips">{"".join(chips)}</div>'
        '<div class="section-title">Churn by language</div>'
        f'<div class="bars">{render_bar_rows(totals, max_total)}</div>'
    )
    if performance_receipts:
        perf = "".join(f"<li>{escape_html(i)}</li>" for i in limit(performance_receipts, 6))
        receipts_html += '<div class="section-title">Performance receipts</div>'
        receipts_html += f'<ul class="tight">{perf}</ul>'

    shipped_cols = []
    for label in ["Explore", "Curate", "Accelerate"]:
        items = shipped_map.get(label, [])
        lis = "".join(f"<li>{escape_html(i)}</li>" for i in limit(items, 6))
        shipped_cols.append(
            '<div class="col">'
            f'<div class="col-title">{escape_html(label)}</div>'
            f'<ul class="tight">{lis}</ul>'
            "</div>"
        )
    shipped_html = f'<div class="cols">{"".join(shipped_cols)}</div>'

    evidence_lines = []
    for e in evidence_items[:12]:
        tags = e.get("tags") or []
        tag_text = f" - {', '.join(tags)}" if tags else ""
        title = (e.get("title") or "").strip()
        title_html = f'<div class="subline">{escape_html(title)}</div>' if title else ""
        headings = e.get("headings") or []
        heading_bits = [h for h in headings if h and h != title][:2]
        headings_html = (
            f'<div class="subline muted">{escape_html(" • ".join(heading_bits))}</div>' if heading_bits else ""
        )
        evidence_lines.append(
            f'<li><span class="mono">{escape_html(e["path"])}</span>'
            f' <span class="muted">({escape_html(str(e["cochange_count"]))}x)</span>'
            f'<span class="muted">{escape_html(tag_text)}</span>{title_html}{headings_html}</li>'
        )
    evidence_html = f'<ul class="tight">{"".join(evidence_lines)}</ul>' if evidence_lines else "<p class=\"muted\">(none)</p>"

    hotspots = sorted(churn_by_path.items(), key=lambda kv: kv[1].total, reverse=True)[:10]
    hotspots_html = render_hotspots_table(hotspots) if hotspots else "<p class=\"muted\">(none)</p>"

    visuals_card = ""
    visuals = dev_graph_visuals or []
    if visuals:
        items = []
        for rel in visuals[:4]:
            base = Path(rel).name
            items.append(
                "<div class=\"visual-item\">"
                f"<img class=\"visual-img\" src=\"{escape_html(rel)}\" />"
                f"<div class=\"visual-caption mono\">{escape_html(base)}</div>"
                "</div>"
            )
        visuals_card = card("Dev Graph Visuals", f'<div class="visual-grid">{"".join(items)}</div>', span2=True)

    story_html = (
        f"<p>{escape_html(story_blurb)}</p>"
        + "<ul>"
        + "".join(f"<li>{escape_html(i)}</li>" for i in limit(cold_open_points, 6))
        + "</ul>"
    )

    return "".join(
        [
            card("The Story", story_html, span2=True),
            card("Shipped Map", shipped_html, span2=True),
            card("Receipts", receipts_html),
            card("Evidence Pack", evidence_html),
            visuals_card,
            card("Hotspots", hotspots_html, span2=True),
            card(
                "Next Scene",
                "<ul>" + "".join(f"<li>{escape_html(i)}</li>" for i in limit(next_scene, 6)) + "</ul>",
            ),
        ]
    )


def build_story_markdown(
    sprint_name: str,
    sprint_dir: Path,
    anchors: list[Path],
    prd_text: str,
    readme_text: str,
    evidence: list[dict[str, Any]],
    churn_by_lang: dict[str, Churn],
    churn_by_path: dict[str, Churn],
    commit_count: int,
    output_name: str,
    dev_graph_meta: Optional[dict[str, Any]] = None,
    dev_graph_visuals: Optional[list[str]] = None,
) -> tuple[list[str], dict[str, list[str]], list[str], str, list[str]]:
    prd_sections = parse_markdown_sections(prd_text) if prd_text else []
    readme_sections = parse_markdown_sections(readme_text) if readme_text else []

    exec_summary = find_section(prd_sections, "Executive Summary")
    success_criteria = find_section(prd_sections, "Success Criteria")
    next_phase = find_section(prd_sections, "Next Phase")
    overview = find_section(readme_sections, "Sprint Overview") or find_section(readme_sections, "Overview")

    build_sections = [
        find_section(readme_sections, "Advanced Interactive Latent Space Explorer"),
        find_section(readme_sections, "Comprehensive Curation"),
        find_section(readme_sections, "Backend Performance"),
    ]

    performance = (
        find_section_exact(readme_sections, "Performance & Scalability")
        or find_section(readme_sections, "Performance & Scalability")
        or find_section(readme_sections, "Performance")
        or find_section(prd_sections, "Monitoring")
    )

    def section_first_paragraph(section: Optional[MdSection], max_chars: int) -> str:
        if not section:
            return ""
        acc: list[str] = []
        for raw in section.lines:
            l = clean_line(raw)
            if not l:
                if acc:
                    break
                continue
            if l.startswith(("-", "*")):
                continue
            if l.startswith("```"):
                break
            acc.append(l)
            if len(" ".join(acc)) >= max_chars:
                break
        return truncate_sentence(" ".join(acc).strip(), max_chars)

    def extract_mermaid_goals(text: str, max_items: int) -> list[str]:
        if "```mermaid" not in text:
            return []
        in_block = False
        items: list[str] = []
        for raw in text.splitlines():
            line = raw.rstrip("\n")
            if line.strip().startswith("```mermaid"):
                in_block = True
                continue
            if in_block and line.strip().startswith("```"):
                break
            if not in_block:
                continue
            m = re.search(r"\"([^\"]+)\"", line)
            if not m:
                continue
            value = clean_line(m.group(1))
            if value:
                items.append(value)
            if len(items) >= max_items:
                break
        return items

    overview_para = section_first_paragraph(overview, 520)
    if overview_para.endswith("..."):
        overview_para = overview_para[:-3].rstrip() + "."
    mermaid_goals = extract_mermaid_goals(readme_text, 6)

    story_bits: list[str] = []
    if overview_para:
        story_bits.append(overview_para)
    if mermaid_goals:
        story_bits.append("Goals: " + "; ".join(mermaid_goals[:2]) + ".")
    story_blurb = " ".join([truncate_sentence(x, 900) for x in story_bits if x]).strip() or "Sprint narrative and receipts."

    cold_open = []
    for src in [prd_text, readme_text]:
        for line in src.splitlines()[:60]:
            l = clean_line(line)
            if not l:
                continue
            if any(k in l.lower() for k in ["status:", "major milestone:", "primary goal:", "sprint duration:"]):
                cold_open.append(l)
    cold_open.extend(section_bullets(exec_summary, 4))
    cold_open = [c for c in (clean_line(x) for x in cold_open) if c]
    seen = set()
    cold_open = [x for x in cold_open if not (x in seen or seen.add(x))]

    plan = []
    plan.extend(section_bullets(success_criteria, 5))
    plan.extend(section_bullets(find_section(prd_sections, "Technology Stack"), 3))
    plan = [p for p in (clean_line(x) for x in plan) if p]

    build = []
    for sec in build_sections:
        build.extend(section_bullets(sec, 12))
    if not build:
        build.extend(section_bullets(find_section(prd_sections, "Primary Achievements"), 18))
    build = [b for b in (clean_line(x) for x in build) if b]

    def bucket(item: str) -> str:
        l = item.lower()
        if any(k in l for k in ["duplicate", "archive", "snapshot", "curat", "merge", "collection"]):
            return "Curate"
        if any(k in l for k in ["cuda", "batch", "fp16", "torch.compile", "throughput", "autosize", "acceleration"]):
            return "Accelerate"
        if any(k in l for k in ["umap", "scatter", "cluster", "lasso", "visual", "deck", "hover", "explor"]):
            return "Explore"
        return "Explore"

    shipped_map: dict[str, list[str]] = {"Explore": [], "Curate": [], "Accelerate": []}
    for b in build:
        shipped_map[bucket(b)].append(b)

    performance_receipts = section_bullets(performance, 6)

    receipts = []
    receipts.extend(performance_receipts)
    total_added = sum(v.added for v in churn_by_lang.values())
    total_deleted = sum(v.deleted for v in churn_by_lang.values())
    receipts.append(f"Commits touching sprint docs: {commit_count}")
    receipts.append(f"Engineering footprint: +{total_added} / -{total_deleted} lines across {len(churn_by_lang)} languages")
    receipts.append(f"Evidence pack: {len(evidence)} linked docs (git co-updated)")
    if dev_graph_meta:
        start_date = dev_graph_meta.get("start_date") or dev_graph_meta.get("start") or ""
        end_date = dev_graph_meta.get("end_date") or dev_graph_meta.get("end") or ""
        if start_date and end_date:
            receipts.append(f"Dev Graph sprint window: {start_date} -> {end_date}")
        if dev_graph_meta.get("commit_count_in_window") is not None:
            receipts.append(f"Dev Graph commits in window: {dev_graph_meta.get('commit_count_in_window')}")
        if dev_graph_meta.get("subgraph_node_count") is not None and dev_graph_meta.get("subgraph_edge_count") is not None:
            receipts.append(
                f"Dev Graph sprint subgraph: {dev_graph_meta.get('subgraph_node_count')} nodes / {dev_graph_meta.get('subgraph_edge_count')} edges"
            )
    receipts = [r for r in (clean_line(x) for x in receipts) if r]

    next_scene = []
    next_scene.extend(section_bullets(next_phase, 8))
    next_scene.extend(collect_child_section_titles(prd_sections, "Next Phase", 6))
    next_scene.extend(section_bullets(find_section(readme_sections, "Next Development Phase"), 8))
    next_scene.extend(collect_child_section_titles(readme_sections, "Next Development Phase", 6))
    next_scene = [n for n in (clean_line(x) for x in next_scene) if n]
    seen2 = set()
    next_scene = [x for x in next_scene if not (x in seen2 or seen2.add(x))]

    lines: list[str] = []
    lines.append(f"# {sprint_name} - Sprint Perspectives")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append("- `SPRINT_PERSPECTIVES_CARDS.html` or `SPRINT_PERSPECTIVES_CARDS.pdf` (cards)")
    lines.append("- `_linked_docs.json` (evidence docs only)")
    lines.append("- `_cochanged_files.json` (all co-changed files)")
    visuals = dev_graph_visuals or []
    if visuals:
        vis_dir = visuals[0].split("/", 1)[0]
        lines.append(f"- `{vis_dir}/` (optional Dev Graph visuals)")
    lines.append("")
    lines.append("## Cold Open")
    lines.append("")
    lines.append(story_blurb)
    lines.append("")
    for i in limit(cold_open, 8):
        lines.append(f"- {i}")
    lines.append("")
    lines.append("## The Plan")
    lines.append("")
    bet = "; ".join(mermaid_goals[:2]).strip()
    lines.append(f"The bet: {bet}." if bet else "The bet: ship the smallest workflow slice that can be verified.")
    lines.append("")
    for i in limit(plan, 10):
        lines.append(f"- {i}")
    lines.append("")
    lines.append("## The Build")
    lines.append("")
    lines.append("What shipped, grouped by user workflow: explore -> curate -> accelerate.")
    lines.append("")
    bucket_intro = {
        "Explore": "Explore is where users build intuition and find the shape of a collection.",
        "Curate": "Curate is where the archive becomes trustworthy (safe, reversible, and consistent).",
        "Accelerate": "Accelerate is what keeps the workflow tactile under real load.",
    }
    for label in ["Explore", "Curate", "Accelerate"]:
        items = shipped_map.get(label, [])
        if not items:
            continue
        lines.append(f"### {label}")
        example = "; ".join(limit(items, 2))
        if example:
            lines.append(f"{bucket_intro.get(label, '')} Shipped: {truncate_sentence(example, 220)}")
        for item in limit(items, 10):
            lines.append(f"- {item}")
        lines.append("")
    lines.append("## The Receipts")
    lines.append("")
    lines.append("Proof lives in numbers and in the paper trail (docs that moved while the sprint story was written).")
    lines.append("")
    for i in limit(receipts, 12):
        lines.append(f"- {i}")
    lines.append("")
    lines.append("### Evidence Pack (git co-updated)")
    lines.append("")
    for item in evidence[:12]:
        title = item.get("title") or ""
        tags = item.get("tags") or []
        headings = item.get("headings") or []
        heading_bits = [h for h in headings if h and h != title][:1]
        meta = [f"{item.get('cochange_count', 0)}x"]
        if tags:
            meta.append(", ".join(tags))
        meta_str = " - " + " | ".join(meta) if meta else ""
        hint = f" - {clean_line(heading_bits[0])}" if heading_bits else ""
        if title:
            lines.append(f"- `{item['path']}`{meta_str} - {clean_line(title)}{hint}")
        else:
            lines.append(f"- `{item['path']}`{meta_str}{hint}")
    lines.append("")
    lines.append("### Engineering Footprint (churn)")
    lines.append("")
    lines.append(f"- Total churn: +{total_added} / -{total_deleted} lines")
    lines.append("")
    lines.append("#### By language")
    for lang, churn in sorted(churn_by_lang.items(), key=lambda kv: kv[1].total, reverse=True)[:12]:
        lines.append(f"- {lang}: +{churn.added} / -{churn.deleted}")
    lines.append("")
    lines.append("#### Hotspots")
    for path, churn in sorted(churn_by_path.items(), key=lambda kv: kv[1].total, reverse=True)[:15]:
        lines.append(f"- `{path}`: +{churn.added} / -{churn.deleted}")
    lines.append("")
    lines.append("## The Next Scene")
    lines.append("")
    lines.append("The loop is live. Next is reducing friction and deepening semantics.")
    lines.append("")
    for i in limit(next_scene, 12):
        lines.append(f"- {i}")
    lines.append("")
    lines.append("## Inputs")
    for a in anchors:
        lines.append(f"- {a.relative_to(sprint_dir).as_posix()}")
    lines.append("")

    (sprint_dir / output_name).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return cold_open, shipped_map, next_scene, story_blurb, performance_receipts


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sprint perspectives from docs + git history")
    parser.add_argument("--sprint", help="Sprint folder name (e.g., sprint-11)")
    parser.add_argument("--all", action="store_true", help="Process all sprint folders")
    parser.add_argument("--include-nonstandard", action="store_true", help="Include nonstandard folders under docs/sprints/")
    parser.add_argument("--keep-html", action="store_true", help="Keep HTML next to PDFs")
    parser.add_argument("--max-evidence", type=int, default=12, help="Max linked evidence docs to include")
    parser.add_argument("--dev-graph-api", default="", help="Optional Dev Graph API base URL (e.g., http://localhost:8080)")
    parser.add_argument(
        "--dev-graph-visuals-dir",
        default=DEFAULT_DEV_GRAPH_VISUALS_DIR,
        help="Optional folder under sprint dir with SVG/PNG receipts to embed",
    )
    parser.add_argument("--md-name", default=DEFAULT_MD_NAME)
    parser.add_argument("--json-name", default=DEFAULT_JSON_NAME)
    parser.add_argument("--pdf-name", default=DEFAULT_PDF_NAME)
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation (HTML only)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    sprints_root = repo_root / "docs" / "sprints"
    if not sprints_root.exists():
        print("docs/sprints not found; run from repo context.", file=sys.stderr)
        return 2

    if not args.sprint and not args.all:
        args.all = True

    if args.sprint:
        sprint_dirs = [sprints_root / args.sprint]
    else:
        sprint_dirs = discover_sprint_dirs(sprints_root, include_nonstandard=args.include_nonstandard)

    for sprint_dir in sprint_dirs:
        if not sprint_dir.exists():
            print("Missing sprint folder:", sprint_dir, file=sys.stderr)
            continue

        anchors = find_anchor_files(sprint_dir)
        if not anchors:
            print("No anchor docs found in:", sprint_dir, file=sys.stderr)
            continue

        rel_anchor_paths = [str(p.relative_to(repo_root)).replace("\\", "/") for p in anchors]
        anchor_path_set = set(rel_anchor_paths)
        commit_ts = collect_anchor_commits(repo_root, rel_anchor_paths)

        candidates = collect_cochanged_candidates(repo_root, anchor_path_set, commit_ts)
        ranked = score_and_rank(candidates)

        all_file_cap = 1500
        all_file_items: list[dict[str, Any]] = []
        evidence_items: list[dict[str, Any]] = []

        for cand in ranked:
            entry: dict[str, Any] = {
                "path": cand.path,
                "cochange_count": cand.cochange_count,
                "last_commit": cand.last_commit,
                "last_commit_ts": cand.last_commit_ts,
                "statuses": sorted(cand.statuses),
                "language": classify_language(cand.path),
                "is_doc": is_doc(cand.path),
            }

            if entry["is_doc"]:
                excerpt = doc_excerpt(repo_root, cand.path)
                entry.update(
                    {
                        "commits": cand.commits,
                        "title": excerpt.get("title", ""),
                        "tags": tag_doc(cand.path, excerpt.get("title", "") or ""),
                        "headings": excerpt.get("headings", []),
                    }
                )
                if len(evidence_items) < args.max_evidence:
                    evidence_items.append(entry)

            if len(all_file_items) < all_file_cap:
                all_file_items.append(entry)

            if len(evidence_items) >= args.max_evidence and len(all_file_items) >= all_file_cap:
                break

        (sprint_dir / args.json_name).write_text(json.dumps(evidence_items, indent=2), encoding="utf-8")
        (sprint_dir / DEFAULT_ALL_FILES_JSON_NAME).write_text(json.dumps(all_file_items, indent=2), encoding="utf-8")

        churn_by_path, churn_by_lang = collect_churn(repo_root, commit_ts.keys())

        prd = next((p for p in anchors if p.name.lower() == "prd.md"), None)
        readme = next((p for p in anchors if p.name.lower() == "readme.md"), None)
        prd_text = safe_read_text(prd) if prd else ""
        readme_text = safe_read_text(readme) if readme else ""

        dev_graph_meta = None
        sprint_number = parse_sprint_number(sprint_dir.name)
        if args.dev_graph_api and sprint_number:
            dev_graph_meta = enrich_from_dev_graph(args.dev_graph_api, sprint_number)
        dev_graph_visuals = discover_dev_graph_visuals(sprint_dir, args.dev_graph_visuals_dir)

        cold_open, shipped_map, next_scene, story_blurb, performance_receipts = build_story_markdown(
            sprint_name=sprint_dir.name,
            sprint_dir=sprint_dir,
            anchors=anchors,
            prd_text=prd_text,
            readme_text=readme_text,
            evidence=evidence_items,
            churn_by_lang=churn_by_lang,
            churn_by_path=churn_by_path,
            commit_count=len(commit_ts),
            output_name=args.md_name,
            dev_graph_meta=dev_graph_meta,
            dev_graph_visuals=dev_graph_visuals,
        )

        title = f"{sprint_dir.name} Perspectives"
        subtitle = (
            markdown_title(readme_text, fallback=sprint_dir.name.replace("-", " ").title())
            if readme_text
            else sprint_dir.name.replace("-", " ").title()
        )
        meta_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        meta = f"{meta_ts} | {len(commit_ts)} commits | {len(evidence_items)} evidence docs"

        cards_html = build_cards_html(
            story_blurb=story_blurb,
            cold_open_points=cold_open,
            shipped_map=shipped_map,
            evidence_items=evidence_items,
            churn_by_lang=churn_by_lang,
            churn_by_path=churn_by_path,
            next_scene=next_scene,
            performance_receipts=performance_receipts,
            commit_count=len(commit_ts),
            dev_graph_meta=dev_graph_meta,
            dev_graph_visuals=dev_graph_visuals,
        )
        html = render_html(title, subtitle, meta, cards_html, footer_left="Pixel Detective - Sprint Perspectives")

        if args.no_pdf:
            html_name = Path(args.pdf_name).with_suffix(".html").name
            (sprint_dir / html_name).write_text(html, encoding="utf-8")
        else:
            pdf_path = sprint_dir / args.pdf_name
            pdf_created = try_write_pdf(html, pdf_path, keep_html=args.keep_html)
            if not pdf_created:
                html_path = pdf_path.with_suffix(".html")
                print("WeasyPrint not available; wrote HTML:", html_path)

        print("Generated perspectives for:", sprint_dir.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
