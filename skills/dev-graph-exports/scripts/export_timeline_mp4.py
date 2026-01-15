import argparse
from pathlib import Path
from typing import Optional


def set_commit_range(page, start: Optional[int], end: Optional[int]) -> None:
    if start is None or end is None:
        return
    label = page.get_by_text('Commit Range')
    container = label.locator('..').locator('..')
    track = container.get_by_test_id('chakra-range-slider-track')
    if track.count() == 0:
        track = container.locator('.chakra-slider__track')
    track = track.first
    thumbs = container.locator('[role=\"slider\"]')
    if thumbs.count() < 2:
        raise RuntimeError('Commit Range sliders not found.')
    track_box = track.bounding_box()
    if not track_box:
        raise RuntimeError('Commit Range slider track not found.')

    min_val = float(thumbs.nth(0).get_attribute('aria-valuemin') or 0)
    max_val = float(thumbs.nth(0).get_attribute('aria-valuemax') or 0)
    if max_val <= min_val:
        raise RuntimeError('Commit Range slider min/max not available.')

    def clamp(value: int) -> int:
        return int(max(min_val, min(max_val, value)))

    start_val = clamp(start)
    end_val = clamp(end)

    def move_thumb(index: int, value: int) -> None:
        ratio = (value - min_val) / (max_val - min_val)
        target_x = track_box['x'] + track_box['width'] * ratio
        target_y = track_box['y'] + track_box['height'] / 2
        thumb = thumbs.nth(index)
        thumb_box = thumb.bounding_box()
        if not thumb_box:
            raise RuntimeError('Slider thumb bounding box not found.')
        page.mouse.move(thumb_box['x'] + thumb_box['width'] / 2, thumb_box['y'] + thumb_box['height'] / 2)
        page.mouse.down()
        page.mouse.move(target_x, target_y)
        page.mouse.up()

    move_thumb(0, start_val)
    move_thumb(1, end_val)
    page.wait_for_timeout(500)


def export_timeline_mp4(url: str, output: Path, headful: bool, range_start: Optional[int], range_end: Optional[int]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        raise RuntimeError("Playwright is required for UI-driven MP4 exports. Install it with `pip install playwright` and then run `playwright install`.") from exc
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(url, wait_until='domcontentloaded', timeout=120000)
        page.wait_for_timeout(5000)

        try:
            page.get_by_text('Loading evolution data...').wait_for(state='detached', timeout=120000)
        except Exception:
            pass

        if range_start is not None and range_end is not None:
            page.get_by_text('Commit Range').wait_for(timeout=60000)
            set_commit_range(page, range_start, range_end)
            page.wait_for_timeout(1500)

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
    parser.add_argument('--range-start', type=int, default=None, help='Start commit index (0-based)')
    parser.add_argument('--range-end', type=int, default=None, help='End commit index (0-based)')
    args = parser.parse_args()

    export_timeline_mp4(args.url, Path(args.output), args.headful, args.range_start, args.range_end)
    print('Saved MP4 to', args.output)


if __name__ == '__main__':
    main()
