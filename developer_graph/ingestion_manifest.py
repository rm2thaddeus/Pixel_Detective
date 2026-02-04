from __future__ import annotations

import json
import hashlib
import os
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ManifestEntry:
    """Single file record inside an ingestion manifest."""

    path: str
    size: int
    mtime: float
    sha1: str

    @classmethod
    def from_path(cls, repo_root: Path, relative_path: str) -> "ManifestEntry":
        absolute = (repo_root / relative_path).resolve()
        stat = absolute.stat()
        return cls(
            path=relative_path.replace("\\", "/"),
            size=stat.st_size,
            mtime=stat.st_mtime,
            sha1=_hash_file(absolute),
        )


@dataclass
class ManifestSnapshot:
    """Serializable manifest snapshot with metadata."""

    entries: Dict[str, ManifestEntry]
    generated_at: str
    last_commit: Optional[str] = None

    def to_json(self) -> Dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "last_commit": self.last_commit,
            "entries": {path: asdict(entry) for path, entry in self.entries.items()},
        }

    @classmethod
    def from_json(cls, data: Dict[str, object]) -> "ManifestSnapshot":
        raw_entries = data.get("entries", {}) or {}
        entries: Dict[str, ManifestEntry] = {}
        for path, payload in raw_entries.items():
            entries[path] = ManifestEntry(
                path=path,
                size=int(payload.get("size", 0)),
                mtime=float(payload.get("mtime", 0.0)),
                sha1=str(payload.get("sha1", "")),
            )
        return cls(
            entries=entries,
            generated_at=str(data.get("generated_at", datetime.utcnow().isoformat() + "Z")),
            last_commit=data.get("last_commit"),
        )


@dataclass
class ManifestDiff:
    """Delta between two manifest snapshots."""

    added: List[str]
    modified: List[str]
    removed: List[str]
    unchanged: List[str]

    @property
    def touched(self) -> List[str]:
        return sorted(set(self.added) | set(self.modified))


class ManifestManager:
    """Builds, stores, and diffs ingestion manifests for incremental runs."""

    def __init__(self, repo_root: str, storage_path: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        if storage_path is None:
            storage_dir = self.repo_root / ".devgraph"
            storage_dir.mkdir(parents=True, exist_ok=True)
            storage_path = storage_dir / "last_manifest.json"
        else:
            storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path = storage_path

    def load_previous(self) -> Optional[ManifestSnapshot]:
        if not self.storage_path.exists():
            return None
        try:
            with self.storage_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            return ManifestSnapshot.from_json(data)
        except Exception:
            return None

    def save_snapshot(self, snapshot: ManifestSnapshot) -> None:
        with self.storage_path.open("w", encoding="utf-8") as handle:
            json.dump(snapshot.to_json(), handle, indent=2, sort_keys=True)

    def build_snapshot(
        self,
        files: Optional[Iterable[str]] = None,
        subpath: Optional[str] = None,
        last_commit: Optional[str] = None,
    ) -> ManifestSnapshot:
        repo_files = list(files) if files is not None else _list_repo_files(self.repo_root)
        if subpath:
            prefix = Path(subpath).as_posix().rstrip("/")
            repo_files = [path for path in repo_files if path.startswith(prefix)]
        entries: Dict[str, ManifestEntry] = {}
        for path in repo_files:
            try:
                entries[path] = ManifestEntry.from_path(self.repo_root, path)
            except FileNotFoundError:
                continue
        return ManifestSnapshot(
            entries=entries,
            generated_at=datetime.utcnow().isoformat() + "Z",
            last_commit=last_commit,
        )

    @staticmethod
    def diff(previous: Optional[ManifestSnapshot], current: ManifestSnapshot) -> ManifestDiff:
        old_entries = previous.entries if previous else {}
        new_entries = current.entries
        added: List[str] = []
        modified: List[str] = []
        unchanged: List[str] = []

        for path, entry in new_entries.items():
            prior = old_entries.get(path)
            if prior is None:
                added.append(path)
            elif prior.sha1 != entry.sha1 or prior.size != entry.size:
                modified.append(path)
            else:
                unchanged.append(path)

        removed = [path for path in old_entries.keys() if path not in new_entries]
        return ManifestDiff(
            added=sorted(added),
            modified=sorted(modified),
            removed=sorted(removed),
            unchanged=sorted(unchanged),
        )


def _list_repo_files(repo_root: Path) -> List[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        pass

    entries: List[str] = []
    for root, _, files in os.walk(repo_root):
        for file_name in files:
            abs_path = Path(root) / file_name
            rel = abs_path.relative_to(repo_root).as_posix()
            entries.append(rel)
    return entries


def _hash_file(path: Path, chunk_size: int = 65536) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()

