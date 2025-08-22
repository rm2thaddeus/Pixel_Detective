"""Git History Service

Provides git-driven temporal data for the Developer Graph.

Key capabilities implemented for Phase 1:
- Parse commit logs (optionally scoped to a file) with authors, timestamps, messages
- Extract commit metadata (hash, author, timestamp, message, files)
- Basic git blame support for a file at a specific commit
- Detect file renames/moves via `git log --follow --name-status`

All temporal data is derived strictly from git. Document timestamps are not used.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from git import Repo


@dataclass
class CommitRecord:
    hash: str
    author_name: str
    author_email: str
    timestamp_iso: str
    message: str
    files_changed: List[str]


class GitHistoryService:
    """High-level wrapper around GitPython for temporal queries.

    Notes:
    - Methods prefer native git plumbing via `Repo.git` where `--follow` is required.
    - All returned timestamps are ISO8601 strings in UTC as provided by git.
    """

    def __init__(self, repo_path: str):
        self.repo_path = str(Path(repo_path).resolve())
        self.repo = Repo(self.repo_path)

    # ---- Commits ----
    def get_commits(self, limit: int = 100, path: Optional[str] = None) -> List[Dict[str, object]]:
        """Return recent commits, optionally restricted to a path (with --follow)."""
        limit = max(1, min(limit, 1000))
        pretty = "%H\t%an\t%ae\t%aI\t%s"
        args = ["--pretty=format:" + pretty, f"-n{limit}"]
        if path:
            # Use --follow for file history across renames
            output = self.repo.git.log("--follow", *args, "--", path)
        else:
            output = self.repo.git.log(*args)

        lines = [line for line in output.split("\n") if line.strip()]
        commits: List[Dict[str, object]] = []
        for line in lines:
            try:
                commit_hash, author_name, author_email, timestamp_iso, message = line.split("\t", 4)
            except ValueError:
                # Skip malformed lines
                continue
            files = self._files_changed_in_commit(commit_hash)
            commits.append(
                {
                    "hash": commit_hash,
                    "author_name": author_name,
                    "author_email": author_email,
                    "timestamp": timestamp_iso,
                    "message": message,
                    "files_changed": files,
                }
            )
        return commits

    def get_commit(self, commit_hash: str) -> Optional[Dict[str, object]]:
        """Return details for a specific commit, including changed files and stats."""
        try:
            commit = self.repo.commit(commit_hash)
        except Exception:
            return None

        stats = commit.stats.total
        files = list(commit.stats.files.keys())
        return {
            "hash": commit.hexsha,
            "author_name": commit.author.name,
            "author_email": commit.author.email,
            "timestamp": commit.committed_datetime.isoformat(),
            "message": commit.message.strip(),
            "files_changed": files,
            "lines_added": stats.get("insertions", 0),
            "lines_deleted": stats.get("deletions", 0),
        }

    # ---- File History ----
    def get_file_history(self, path: str, limit: int = 200) -> List[Dict[str, object]]:
        """Return history events for a file, following renames/moves.

        Output includes commit hash, timestamp, author, message, and change_type
        (e.g., M/A/D/Rxxx where R is rename score).
        """
        limit = max(1, min(limit, 2000))
        pretty = "%H\t%an\t%ae\t%aI\t%s"
        log_output = self.repo.git.log(
            "--follow",
            f"-n{limit}",
            "--name-status",
            "--pretty=format:" + pretty,
            "--",
            path,
        )

        events: List[Dict[str, object]] = []
        current_meta: Optional[List[str]] = None
        for raw in log_output.split("\n"):
            if not raw.strip():
                continue
            if "\t" in raw and len(raw.split("\t")) >= 5:
                # New commit meta line
                current_meta = raw.split("\t", 4)
                continue
            # Name-status lines follow each commit meta
            if current_meta is None:
                continue
            status_line = raw.strip()
            parts = status_line.split("\t")
            change = parts[0]
            file_paths = parts[1:]
            commit_hash, author_name, author_email, timestamp_iso, message = current_meta
            if change.startswith("R") and len(file_paths) == 2:
                src, dst = file_paths
                events.append(
                    {
                        "hash": commit_hash,
                        "author_name": author_name,
                        "author_email": author_email,
                        "timestamp": timestamp_iso,
                        "message": message,
                        "change_type": change,  # e.g. R100
                        "src_path": src,
                        "dst_path": dst,
                    }
                )
            else:
                events.append(
                    {
                        "hash": commit_hash,
                        "author_name": author_name,
                        "author_email": author_email,
                        "timestamp": timestamp_iso,
                        "message": message,
                        "change_type": change,  # e.g. M/A/D
                        "path": file_paths[0] if file_paths else path,
                    }
                )
        return events

    def blame_file_at_commit(self, path: str, commit_hash: str) -> List[Dict[str, str]]:
        """Return blame info for a file at a specific commit.

        Each entry includes author_email, author_name, and line text (without newlines).
        """
        blame_output = self.repo.git.blame(commit_hash, "--", path)
        result: List[Dict[str, str]] = []
        for line in blame_output.split("\n"):
            if not line:
                continue
            # Git blame porcelain-like: hash (AuthorName YYYY-MM-DD ...) line
            try:
                metadata, text = line.split(") ", 1)
                # metadata like: "<hash> (<Author Name> <date> <time> <tz> <lineno>)"
                # Extract author name between first '(' and last ')' chunk
                author_segment = metadata.split("(", 1)[1]
                author_name = author_segment.split(" ")[0].strip()
            except Exception:
                author_name = "Unknown"
                text = line
            result.append({"author_name": author_name, "line": text})
        return result

    # ---- Helpers ----
    def _files_changed_in_commit(self, commit_hash: str) -> List[str]:
        try:
            commit = self.repo.commit(commit_hash)
            return list(commit.stats.files.keys())
        except Exception:
            return []


