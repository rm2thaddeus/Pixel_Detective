import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def export_timeline_mp4(url: str, output: Path, headful: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(url, wait_until='networkidle')
        page.wait_for_timeout(3000)

        export_button = page.get_by_role('button', name='Export MP4')
        if export_button.count() == 0:
            raise RuntimeError('Export MP4 button not found on the page.')

        for _ in range(60):
            if export_button.is_enabled():
                break
            page.wait_for_timeout(1000)
        else:
            raise RuntimeError('Export MP4 button never became enabled.')

        with page.expect_download(timeout=600000) as download_info:
            export_button.click()
        download = download_info.value
        download.save_as(str(output))
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description='Export Timeline MP4 from Dev Graph UI')
    parser.add_argument('--url', default='http://localhost:3001/dev-graph/timeline/svg')
    parser.add_argument('--output', default='exports/dev-graph/timeline-export.mp4')
    parser.add_argument('--headful', action='store_true', help='Run Chromium with a visible window')
    args = parser.parse_args()

    export_timeline_mp4(args.url, Path(args.output), args.headful)
    print('Saved MP4 to', args.output)


if __name__ == '__main__':
    main()
