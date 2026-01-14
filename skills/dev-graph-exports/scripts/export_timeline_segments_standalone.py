import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


BG = '#0b0e13'
FG = '#e5e7eb'
ACCENT = '#3182ce'
MUTED = '#94a3b8'


def sanitize_text(text: str) -> str:
    return text.encode('ascii', errors='replace').decode('ascii')


def fetch_commits(api_base: str, limit: int, max_files: int) -> tuple[list[dict], int]:
    url = f"{api_base.rstrip('/')}/api/v1/dev-graph/evolution/timeline?limit={limit}&max_files_per_commit={max_files}"
    with urlopen(url) as response:
        payload = json.load(response)
    commits = payload.get('commits', [])
    total = payload.get('total_commits') or len(commits)
    return commits, int(total)


def render_frame(commits: list[dict], idx: int, out_png: Path, out_svg: Path) -> None:
    total = len(commits)
    current = commits[idx]
    xs = list(range(idx + 1))
    sizes = []
    colors = []
    for i in xs:
        files = commits[i].get('files') or []
        size = min(120, 20 + (len(files) * 4))
        sizes.append(size)
        colors.append(ACCENT if i == idx else '#475569')

    fig, ax = plt.subplots(figsize=(12, 4), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_position([0, 0, 1, 1])

    ax.plot([0, max(1, idx)], [0, 0], color='#1f2937', linewidth=2, zorder=1)
    ax.scatter(xs, [0] * len(xs), s=sizes, c=colors, zorder=2)

    message = sanitize_text(current.get('message', '')[:90])
    author = sanitize_text(current.get('author', ''))
    ax.text(0, 0.6, 'Dev Graph Timeline', color=FG, fontsize=14, fontweight='bold')
    ax.text(0, 0.35, f"Commit {idx + 1} / {total}", color=MUTED, fontsize=10)
    ax.text(0, 0.15, message, color=FG, fontsize=10)
    ax.text(0, -0.25, f"{current.get('hash', '')[:8]}  {author}", color=MUTED, fontsize=9)

    ax.set_xlim(-2, max(5, idx + 2))
    ax.set_ylim(-1, 1)
    ax.axis('off')

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, facecolor=BG)
    fig.savefig(out_svg, facecolor=BG)
    plt.close(fig)


def run_ffmpeg(frame_pattern: Path, output_path: Path, fps: int) -> None:
    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(fps),
        '-i', str(frame_pattern),
        '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def run_gif(frame_pattern: Path, output_path: Path, fps: int) -> None:
    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(fps),
        '-i', str(frame_pattern),
        '-vf', 'fps=10,scale=960:-1:flags=lanczos',
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def export_segment(commits: list[dict], start: int, end: int, label: str, output_dir: Path, fps: int) -> None:
    segment = commits[start:end + 1]
    frame_dir = output_dir / 'timeline-frames' / label
    frame_dir.mkdir(parents=True, exist_ok=True)

    for idx, commit in enumerate(segment):
        global_index = start + idx
        frame_idx = idx + 1
        out_png = frame_dir / f'frame_{frame_idx:04d}.png'
        out_svg = frame_dir / f'frame_{frame_idx:04d}.svg'
        render_frame(commits, global_index, out_png, out_svg)

    mp4_path = output_dir / f'timeline-{label}.mp4'
    gif_path = output_dir / f'timeline-{label}.gif'
    run_ffmpeg(frame_dir / 'frame_%04d.png', mp4_path, fps)
    run_gif(frame_dir / 'frame_%04d.png', gif_path, fps)


def main() -> None:
    parser = argparse.ArgumentParser(description='Standalone timeline video export using Dev Graph API')
    parser.add_argument('--api', default='http://localhost:8080')
    parser.add_argument('--output-dir', default='exports/dev-graph')
    parser.add_argument('--limit', type=int, default=5000)
    parser.add_argument('--max-files', type=int, default=50)
    parser.add_argument('--fps', type=int, default=6)
    args = parser.parse_args()

    commits, total = fetch_commits(args.api, args.limit, args.max_files)
    if not commits:
        raise SystemExit('No commits returned from API')

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ranges = [
        (0, min(69, len(commits) - 1), 'commits-1-70'),
        (69, min(199, len(commits) - 1), 'commits-70-200'),
    ]
    if len(commits) > 199:
        ranges.append((199, len(commits) - 1, 'commits-200-plus'))

    for start, end, label in ranges:
        if start > end:
            continue
        export_segment(commits, start, end, label, output_dir, args.fps)
        print('Saved segment', label)


if __name__ == '__main__':
    main()
