"""Sprint mapping utilities.

Map sprint windows (ISO8601 start/end) to git commit ranges using git history.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

from git import Repo


_START_RE = re.compile(r"Start Date\W*:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE)
_END_RE = re.compile(r"End Date\W*:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE)
_SECTION_RE = re.compile(
    r"^###[^\n]*?Sprint\s+(\d+)(?::\s*([^\n]+))?\n(?P<body>.*?)(?=^###|\Z)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)


class SprintMapper:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.repo = Repo(repo_path)
        self._cached_windows: Optional[Dict[str, Dict[str, str]]] = None

    # -------------------- Public API --------------------
    def map_sprint_range(self, number: str, start_iso: str, end_iso: str) -> Dict[str, object]:
        """Return commit range info for a sprint window.

        Strategy: use `git log --since --until` ordered by date, choose
        first hash as start and last hash as end. If no commits exist,
        return an empty mapping.
        """
        fmt = "%H\t%aI\t%s"
        try:
            out = self.repo.git.log(
                "--since",
                start_iso,
                "--until",
                end_iso,
                "--date-order",
                "--pretty=format:" + fmt,
            )
        except Exception:
            return {
                "number": number,
                "start": start_iso,
                "end": end_iso,
                "commit_range": [],
                "count": 0,
            }

        lines = [line for line in out.split("\n") if line.strip()]
        if not lines:
            return {
                "number": number,
                "start": start_iso,
                "end": end_iso,
                "commit_range": [],
                "count": 0,
            }

        hashes: List[str] = []
        for line in lines:
            try:
                commit_hash, _ts, _msg = line.split("\t", 2)
            except ValueError:
                continue
            hashes.append(commit_hash)

        return {
            "number": number,
            "start": start_iso,
            "end": end_iso,
            "commit_range": [hashes[0], hashes[-1]] if hashes else [],
            "count": len(hashes),
        }

    def get_sprint_windows(self, refresh: bool = False) -> Dict[str, Dict[str, str]]:
        """Return cached sprint windows keyed by sprint number."""
        if refresh or self._cached_windows is None:
            self._cached_windows = self._build_sprint_windows()
        # Return a shallow copy so callers cannot mutate cached state.
        return {k: v.copy() for k, v in (self._cached_windows or {}).items()}

    def map_all_sprints(self) -> Dict[str, object]:
        """Compute sprint windows and attach commit-span metadata."""
        windows = self.get_sprint_windows(refresh=True)
        snapshots = []
        for number, window in sorted(windows.items(), key=lambda item: int(item[0])):
            start_iso = window.get("start")
            end_iso = window.get("end")
            if not start_iso or not end_iso:
                continue
            metrics = self.map_sprint_range(number, start_iso, end_iso)
            snapshot = {
                "number": number,
                "name": window.get("name"),
                "start": start_iso,
                "end": end_iso,
                "commit_count": metrics.get("count", 0),
                "commit_range": metrics.get("commit_range", []),
            }
            snapshots.append(snapshot)
        return {"count": len(snapshots), "windows": snapshots}

    # -------------------- Internal helpers --------------------
    def _build_sprint_windows(self) -> Dict[str, Dict[str, str]]:
        windows = self._parse_planning_status()
        if not windows:
            return {}
        self._augment_with_sprint_docs(windows)
        self._fill_missing_end_dates(windows)
        return windows

    def _planning_status_path(self) -> Path:
        return self.repo_path / "docs" / "sprints" / "planning" / "SPRINT_STATUS.md"

    def _parse_planning_status(self) -> Dict[str, Dict[str, str]]:
        planning_file = self._planning_status_path()
        if not planning_file.exists():
            return {}

        try:
            text = planning_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = planning_file.read_text(encoding="utf-8", errors="ignore")

        windows: Dict[str, Dict[str, str]] = {}
        for match in _SECTION_RE.finditer(text):
            number = match.group(1)
            raw_name = match.group(2) or ""
            body = match.group("body") or ""
            start_match = _START_RE.search(body)
            end_match = _END_RE.search(body)
            windows[number] = {
                "number": number,
                "name": raw_name.strip() or None,
                "start": start_match.group(1) if start_match else None,
                "end": end_match.group(1) if end_match else None,
            }
        return windows

    def _augment_with_sprint_docs(self, windows: Dict[str, Dict[str, str]]) -> None:
        base_dir = self.repo_path / "docs" / "sprints"
        if not base_dir.exists():
            return

        for number, window in windows.items():
            sprint_dir = base_dir / f"sprint-{int(number):02d}"
            if not sprint_dir.exists():
                continue

            for md_path in sprint_dir.rglob("*.md"):
                try:
                    text = md_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    text = md_path.read_text(encoding="utf-8", errors="ignore")
                if window.get("start") is None:
                    start_match = _START_RE.search(text)
                    if start_match:
                        window["start"] = start_match.group(1)
                if window.get("end") is None:
                    end_match = _END_RE.search(text)
                    if end_match:
                        window["end"] = end_match.group(1)
                if window.get("start") and window.get("end"):
                    break

    def _fill_missing_end_dates(self, windows: Dict[str, Dict[str, str]]) -> None:
        sortable: List[Tuple[str, Dict[str, str]]] = [
            (number, window)
            for number, window in windows.items()
            if window.get("start")
        ]
        sortable.sort(key=lambda item: (item[1]["start"], int(item[0])))

        for idx, (number, window) in enumerate(sortable):
            if window.get("end"):
                continue

            start_iso = window.get("start")
            if not start_iso:
                continue
            try:
                start_dt = datetime.fromisoformat(start_iso)
            except ValueError:
                continue

            next_start_iso = None
            if idx + 1 < len(sortable):
                next_start_iso = sortable[idx + 1][1].get("start")

            if next_start_iso:
                try:
                    next_start_dt = datetime.fromisoformat(next_start_iso)
                    end_dt = next_start_dt - timedelta(days=1)
                except ValueError:
                    end_dt = start_dt + timedelta(days=13)
            else:
                # Default sprint length: two weeks
                end_dt = start_dt + timedelta(days=13)

            window["end"] = end_dt.date().isoformat()
