"""Sprint mapping utilities.

Map sprint windows (ISO8601 start/end) to git commit ranges using git history.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

from git import Repo


_START_RE = re.compile(r"\*\*Start Date\*\*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE)
_END_RE = re.compile(r"\*\*End Date\*\*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE)
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
        """Compute sprint windows using git commit timestamps from sprint documents."""
        snapshots = []
        
        # Get all sprint directories
        sprint_dirs = self._get_sprint_directories()
        
        for sprint_dir in sprint_dirs:
            number = sprint_dir["number"]
            name = sprint_dir["name"]
            
            # Get git timestamps for this sprint's documents
            git_timestamps = self._get_sprint_git_timestamps(sprint_dir["path"])
            
            if not git_timestamps:
                continue
                
            # Determine sprint window from git activity
            start_iso, end_iso = self._determine_sprint_window(git_timestamps)
            
            if not start_iso or not end_iso:
                continue
                
            # Map commits in this window
            metrics = self.map_sprint_range(number, start_iso, end_iso)
            
            snapshot = {
                "number": number,
                "name": name,
                "start": start_iso,
                "end": end_iso,
                "commit_count": metrics.get("count", 0),
                "commit_range": metrics.get("commit_range", []),
                "git_timestamps": git_timestamps
            }
            snapshots.append(snapshot)
            
        return {"count": len(snapshots), "windows": snapshots}

    # -------------------- Internal helpers --------------------
    
    def _get_sprint_directories(self) -> List[Dict[str, str]]:
        """Get all sprint directories with their numbers and names."""
        sprint_dirs = []
        base_dir = self.repo_path / "docs" / "sprints"
        
        if not base_dir.exists():
            return sprint_dirs
            
        for item in base_dir.iterdir():
            if not item.is_dir():
                continue
                
            if item.name.startswith("sprint-"):
                number = item.name.split("-")[1]
                name = f"sprint-{number}"
            elif item.name.startswith("s-"):
                number = item.name.split("-")[1]
                name = item.name
            elif item.name.startswith("critical-"):
                number = "critical"
                name = item.name
            else:
                continue
                
            sprint_dirs.append({
                "number": number,
                "name": name,
                "path": str(item)
            })
            
        return sorted(sprint_dirs, key=lambda x: int(x["number"]) if x["number"].isdigit() else 999)
    
    def _get_sprint_git_timestamps(self, sprint_path: str) -> List[Dict[str, str]]:
        """Get git commit timestamps for all files in a sprint directory."""
        try:
            repo = Repo(self.repo_path)
            timestamps = []
            
            sprint_path_obj = Path(sprint_path)
            if not sprint_path_obj.exists():
                return timestamps
                
            # Get all markdown files in the sprint directory
            for md_file in sprint_path_obj.rglob("*.md"):
                try:
                    # Get git log for this file
                    commits = list(repo.iter_commits(paths=str(md_file.relative_to(self.repo_path))))
                    
                    if commits:
                        # Get first and last commit timestamps
                        first_commit = commits[-1]  # Oldest commit
                        last_commit = commits[0]    # Newest commit
                        
                        timestamps.append({
                            "file": str(md_file.relative_to(self.repo_path)),
                            "first_commit": first_commit.hexsha,
                            "first_timestamp": first_commit.committed_datetime.isoformat(),
                            "last_commit": last_commit.hexsha,
                            "last_timestamp": last_commit.committed_datetime.isoformat(),
                            "commit_count": len(commits)
                        })
                        
                except Exception as e:
                    # Skip files that can't be processed
                    continue
                    
            return timestamps
            
        except Exception as e:
            return []
    
    def _determine_sprint_window(self, git_timestamps: List[Dict[str, str]]) -> Tuple[str, str]:
        """Determine sprint start and end dates from git timestamps."""
        if not git_timestamps:
            return None, None
            
        # Find the earliest first commit and latest last commit
        earliest_start = min(ts["first_timestamp"] for ts in git_timestamps)
        latest_end = max(ts["last_timestamp"] for ts in git_timestamps)
        
        # Add some buffer (e.g., 1 day before start, 1 day after end)
        from datetime import datetime, timedelta
        
        try:
            start_dt = datetime.fromisoformat(earliest_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(latest_end.replace('Z', '+00:00'))
            
            # Add buffer
            start_dt = start_dt - timedelta(days=1)
            end_dt = end_dt + timedelta(days=1)
            
            return start_dt.isoformat(), end_dt.isoformat()
            
        except Exception:
            return earliest_start, latest_end

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
