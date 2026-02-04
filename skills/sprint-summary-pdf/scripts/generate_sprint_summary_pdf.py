import argparse
import re
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'sprint_cards_template.html'
DEFAULT_OUTPUT_NAME = 'SPRINT_SUMMARY_CARDS.pdf'

SECTION_ORDER = [
    ('Goal', 'goal'),
    ('Highlights', 'highlights'),
    ('Metrics', 'metrics'),
    ('Risks and Gaps', 'risks'),
    ('Next Steps', 'next'),
    ('Notes', 'notes'),
]

KEYWORDS = {
    'goal': ['goal', 'objective', 'aim', 'theme'],
    'highlights': ['delivered', 'completed', 'achievement', 'feature', 'shipped', 'success', 'wins'],
    'metrics': ['ms', 's ', 'sec', 'seconds', 'fps', '%', 'x ', 'target', 'performance'],
    'risks': ['risk', 'gap', 'issue', 'uncompleted', 'deviation', 'blocking'],
    'next': ['next', 'transition', 'planned', 'follow-up', 'roadmap'],
}

HEADER_KEYS = ['status', 'sprint duration', 'date']


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return path.read_text(encoding='utf-8', errors='replace')


def normalize_line(line: str) -> str:
    line = re.sub(r'`+', '', line)
    line = re.sub(r'\*\*', '', line)
    line = re.sub(r'__', '', line)
    return line.strip()


def extract_title(texts: list[str], sprint_name: str) -> str:
    for text in texts:
        for line in text.splitlines():
            if line.startswith('#'):
                cleaned = normalize_line(line.lstrip('#').strip())
                if cleaned:
                    return cleaned
    return sprint_name.replace('-', ' ').title()


def extract_meta(texts: list[str]) -> str:
    meta_lines = []
    for text in texts:
        for line in text.splitlines():
            lower = line.lower()
            if any(key in lower for key in HEADER_KEYS):
                cleaned = normalize_line(line)
                if cleaned:
                    meta_lines.append(cleaned)
    return ' | '.join(dict.fromkeys(meta_lines))


def extract_bullets(texts: list[str]) -> list[str]:
    bullets = []
    for text in texts:
        for line in text.splitlines():
            if re.match(r'^\s*[-*]\s+', line):
                cleaned = normalize_line(re.sub(r'^\s*[-*]\s+', '', line))
                if cleaned:
                    bullets.append(cleaned)
    return bullets


def categorize_bullets(bullets: list[str]) -> dict:
    sections = {key: [] for _, key in SECTION_ORDER}
    for line in bullets:
        lower = line.lower()
        matched = False
        for key, keywords in KEYWORDS.items():
            if any(word in lower for word in keywords):
                sections[key].append(line)
                matched = True
                break
        if not matched:
            sections['notes'].append(line)
    return sections


def limit_items(items: list[str], max_items: int) -> list[str]:
    return items[:max_items]


def build_cards(sections: dict) -> str:
    cards = []
    for title, key in SECTION_ORDER:
        items = [i for i in sections.get(key, []) if i]
        if not items:
            continue
        items = limit_items(items, 6)
        bullet_html = ''.join(f'<li>{i}</li>' for i in items)
        cards.append(f'<div class="card"><h3>{title}</h3><ul>{bullet_html}</ul></div>')
    return ''.join(cards)


def render_html(title: str, subtitle: str, meta: str, cards_html: str, footer_left: str) -> str:
    template = read_text(TEMPLATE_PATH)
    return (
        template
        .replace('{{TITLE}}', title)
        .replace('{{SUBTITLE}}', subtitle)
        .replace('{{META}}', meta)
        .replace('{{CARDS}}', cards_html)
        .replace('{{FOOTER_LEFT}}', footer_left)
    )


def write_pdf(html: str, output_path: Path, keep_html: bool) -> bool:
    html_path = output_path.with_suffix('.html')
    html_path.write_text(html, encoding='utf-8')
    try:
        from weasyprint import HTML
    except Exception:
        print('WeasyPrint is not available. HTML output created:', html_path)
        return False

    HTML(string=html, base_url=str(output_path.parent)).write_pdf(str(output_path))
    if not keep_html:
        html_path.unlink(missing_ok=True)
    return True


def collect_sprint_files(sprint_dir: Path) -> list[Path]:
    patterns = [
        'README.md',
        'PRD.md',
        '*SUMMARY*.md',
        'completion-summary*.md',
        'mindmap*.md',
    ]
    files = []
    for pattern in patterns:
        files.extend(sorted(sprint_dir.glob(pattern)))
    return files


def process_sprint(sprint_dir: Path, keep_html: bool, output_name: str) -> tuple[Path, bool]:
    sprint_name = sprint_dir.name
    files = collect_sprint_files(sprint_dir)
    texts = [read_text(path) for path in files if path.exists()]

    title = extract_title(texts, sprint_name)
    meta = extract_meta(texts)
    bullets = extract_bullets(texts)

    if not bullets:
        bullets = [f'No bullet sections found in {sprint_name}.']

    sections = categorize_bullets(bullets)
    cards_html = build_cards(sections)
    if not cards_html:
        cards_html = '<div class="card"><h3>Summary</h3><ul><li>No summary data found.</li></ul></div>'

    subtitle = sprint_name.replace('-', ' ').title()
    footer_left = 'Generated from docs/sprints'
    html = render_html(title, subtitle, meta, cards_html, footer_left)

    output_path = sprint_dir / output_name
    pdf_created = write_pdf(html, output_path, keep_html)
    return output_path, pdf_created


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate sprint summary PDFs')
    parser.add_argument('--sprint', help='Sprint folder name (e.g., sprint-11)')
    parser.add_argument('--all', action='store_true', help='Process all sprint folders')
    parser.add_argument('--keep-html', action='store_true', help='Keep HTML files next to PDFs')
    parser.add_argument('--output-name', default=DEFAULT_OUTPUT_NAME)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    sprints_root = repo_root / 'docs' / 'sprints'

    if not sprints_root.exists():
        raise SystemExit('docs/sprints not found. Run from repo context.')

    if not args.sprint and not args.all:
        args.all = True

    if args.sprint:
        targets = [sprints_root / args.sprint]
    elif args.all:
        targets = [p for p in sprints_root.iterdir() if p.is_dir() and p.name.startswith('sprint-')]
    else:
        raise SystemExit('Specify --sprint sprint-XX or --all')

    for sprint_dir in sorted(targets):
        if not sprint_dir.exists():
            print('Missing sprint folder:', sprint_dir)
            continue
        output_path, pdf_created = process_sprint(sprint_dir, args.keep_html, args.output_name)
        status = 'PDF created' if pdf_created else 'HTML created (PDF missing)'
        print(f'{status}: {output_path}')


if __name__ == '__main__':
    main()
