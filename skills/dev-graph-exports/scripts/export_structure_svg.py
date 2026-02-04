import argparse
from pathlib import Path


def set_select_value(page, label_text: str, value: str) -> None:
    if not value:
        return
    label = page.get_by_text(label_text)
    select = label.locator('..').locator('select')
    if select.count() == 0:
        raise RuntimeError(f'Unable to find select for {label_text}')
    select.select_option(value=value)


def set_slider_value(page, label_text: str, value: int) -> None:
    label = page.get_by_text(label_text)
    slider = label.locator('..').locator('input[type="range"]')
    if slider.count() == 0:
        return
    page.evaluate(
        """
        (el, val) => {
          el.value = String(val);
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        slider,
        value,
    )


def export_structure_svg(url: str, output: Path, headful: bool, source_type: str, target_type: str, relation_type: str, max_nodes: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        raise RuntimeError("Playwright is required for UI-driven SVG exports. Install it with `pip install playwright` and then run `playwright install`.") from exc
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(url, wait_until='networkidle')
        page.wait_for_timeout(2000)

        if source_type:
            set_select_value(page, 'From Type:', source_type)
            page.wait_for_timeout(1000)
        if target_type:
            set_select_value(page, 'To Type:', target_type)
            page.wait_for_timeout(1000)
        if relation_type:
            set_select_value(page, 'Relation Type:', relation_type)
            page.wait_for_timeout(1000)
        if max_nodes:
            set_slider_value(page, 'Max Nodes:', max_nodes)
            page.wait_for_timeout(1000)

        button = page.get_by_role('button', name='Export SVG')
        if button.count() == 0:
            raise RuntimeError('Export SVG button not found on the page.')

        with page.expect_download(timeout=120000) as download_info:
            button.click()
        download = download_info.value
        download.save_as(str(output))
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description='Export Structure View SVG from Dev Graph UI')
    parser.add_argument('--url', default='http://localhost:3001/dev-graph/structure')
    parser.add_argument('--output', default='exports/dev-graph/structure-graph.svg')
    parser.add_argument('--headful', action='store_true', help='Run Chromium with a visible window')
    parser.add_argument('--source-type', default='', help='From Type dropdown value')
    parser.add_argument('--target-type', default='', help='To Type dropdown value')
    parser.add_argument('--relation-type', default='', help='Relation Type dropdown value')
    parser.add_argument('--max-nodes', type=int, default=0, help='Max Nodes slider value')
    args = parser.parse_args()

    export_structure_svg(
        args.url,
        Path(args.output),
        args.headful,
        args.source_type,
        args.target_type,
        args.relation_type,
        args.max_nodes,
    )
    print('Saved SVG to', args.output)


if __name__ == '__main__':
    main()
