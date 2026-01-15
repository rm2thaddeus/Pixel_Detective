import argparse
from pathlib import Path
from typing import Optional


def find_timeline_svg(page) -> Optional[str]:
    script = """
    () => {
      const svgs = Array.from(document.querySelectorAll('svg'));
      const pick = svgs.find((svg) => {
        const w = parseFloat(svg.getAttribute('width') || '0');
        const h = parseFloat(svg.getAttribute('height') || '0');
        if (w >= 1000 || h >= 500) return true;
        const viewBox = svg.getAttribute('viewBox') || '';
        return viewBox.includes('1200') || viewBox.includes('600');
      });
      if (!pick) return null;
      const serializer = new XMLSerializer();
      return serializer.serializeToString(pick);
    }
    """
    return page.evaluate(script)


def export_timeline_svgs(url: str, output_dir: Path, start: int, count: int, headful: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        raise RuntimeError("Playwright is required for UI-driven SVG exports. Install it with `pip install playwright` and then run `playwright install`.") from exc
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until='networkidle')
        page.wait_for_timeout(3000)

        reset_button = page.get_by_role('button', name='Reset to Range Start')
        if reset_button.count() > 0:
            reset_button.click()
            page.wait_for_timeout(1000)

        next_button = page.get_by_role('button', name='Next')
        if next_button.count() == 0:
            raise RuntimeError('Next button not found on the timeline page.')

        for _ in range(start):
            next_button.click()
            page.wait_for_timeout(800)

        for idx in range(count):
            svg_text = find_timeline_svg(page)
            if not svg_text:
                raise RuntimeError('Timeline SVG not found in the page.')
            output_path = output_dir / f'commit_{start + idx + 1:04d}.svg'
            output_path.write_text(svg_text, encoding='utf-8')
            if next_button.is_disabled():
                break
            next_button.click()
            page.wait_for_timeout(800)

        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description='Export per-commit SVG frames from Dev Graph timeline')
    parser.add_argument('--url', default='http://localhost:3001/dev-graph/timeline/svg')
    parser.add_argument('--output-dir', default='exports/dev-graph/timeline-frames')
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--count', type=int, default=10)
    parser.add_argument('--headful', action='store_true', help='Run Chromium with a visible window')
    args = parser.parse_args()

    export_timeline_svgs(args.url, Path(args.output_dir), args.start, args.count, args.headful)
    print('Saved SVG frames to', args.output_dir)


if __name__ == '__main__':
    main()
