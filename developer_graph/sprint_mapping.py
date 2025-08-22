"""Sprint mapping utilities.

Map sprint windows (ISO8601 start/end) to git commit ranges using git history.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from git import Repo


class SprintMapper:
    def __init__(self, repo_path: str):
        self.repo = Repo(repo_path)

    def map_sprint_range(self, number: str, start_iso: str, end_iso: str) -> Dict[str, object]:
        """Return commit range info for a sprint window.

        Strategy: use `git log --since --until` ordered by date, choose
        first hash as start and last hash as end. If no commits exist,
        return an empty mapping.
        """
        fmt = "%H\t%aI\t%s"
        try:
            out = self.repo.git.log(
                "--since", start_iso,
                "--until", end_iso,
                "--date-order",
                "--pretty=format:" + fmt,
            )
        except Exception:
            return {"number": number, "start": start_iso, "end": end_iso, "commit_range": [], "count": 0}

        lines = [l for l in out.split("\n") if l.strip()]
        if not lines:
            return {"number": number, "start": start_iso, "end": end_iso, "commit_range": [], "count": 0}

        hashes: List[str] = []
        for line in lines:
            try:
                h, _ts, _msg = line.split("\t", 2)
            except ValueError:
                continue
            hashes.append(h)
        start_hash = hashes[0]
        end_hash = hashes[-1]
        return {
            "number": number,
            "start": start_iso,
            "end": end_iso,
            "commit_range": [start_hash, end_hash],
            "count": len(hashes),
        }


