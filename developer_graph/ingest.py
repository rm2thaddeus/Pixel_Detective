"""Developer Graph Ingestion Utilities.

This module parses sprint documentation, git history and dependency files to
populate a Neo4j Developer Graph. It covers the following node types:
`Sprint`, `Document`, `Requirement`, `Commit`, `File`, `Release`, `Library`,
`Idea` and `Attempt`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Iterable, Optional, Tuple

from git import Repo
from neo4j import GraphDatabase


REQ_PATTERN = re.compile(r"\b(?:FR|NFR)-\d{2}-\d{2}\b")


class DevGraphIngester:
    """Parse repository metadata and populate the Developer Graph."""

    def __init__(self, repo_path: str, neo4j_uri: str, user: str, password: str):
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))

    # --- Document Parsing ---
    def parse_sprints(self) -> List[Dict[str, str]]:
        """Parse sprint folders and statuses."""
        base = Path(self.repo_path) / "docs" / "sprints"
        sprints: List[Dict[str, str]] = []
        status_file = base / "planning" / "SPRINT_STATUS.md"
        status_map = self._parse_sprint_status(status_file)
        for item in base.iterdir():
            if item.is_dir() and item.name.startswith("sprint-"):
                num = item.name.split("-")[1]
                prd = item / "PRD.md"
                sprints.append({
                    "number": num,
                    "path": str(item),
                    "prd": str(prd) if prd.exists() else None,
                    "status": status_map.get(num, "unknown"),
                })
        return sprints

    def _parse_sprint_status(self, path: Path) -> Dict[str, str]:
        if not path.exists():
            return {}
        text = path.read_text(encoding="utf-8")
        status_map: Dict[str, str] = {}
        pattern = re.compile(r"Sprint\s+(\d+).*?Status\*\*:\s*\*\*(.*?)\*\*", re.S)
        for match in pattern.finditer(text):
            num, status = match.groups()
            status_map[num] = status.strip()
        return status_map

    def extract_requirements(self, prd_path: str) -> List[Dict[str, str]]:
        """Extract FR/NFR requirements from a PRD markdown file."""
        reqs = []
        if not prd_path:
            return reqs
        text = Path(prd_path).read_text(encoding="utf-8")
        for line in text.splitlines():
            match = REQ_PATTERN.search(line)
            if match:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 4:
                    reqs.append({
                        "id": match.group(),
                        "description": parts[1],
                        "priority": parts[2],
                        "criteria": parts[3],
                        "raw": line.strip(),
                    })
        return reqs

    def extract_ideas(self, prd_path: str) -> List[str]:
        """Extract high level ideas or objectives from a PRD."""
        ideas: List[str] = []
        if not prd_path:
            return ideas
        text = Path(prd_path).read_text(encoding="utf-8")
        capture = False
        for line in text.splitlines():
            if line.lower().startswith("## 2.1") or "objective" in line.lower():
                capture = True
                continue
            if capture:
                if line.startswith("##"):
                    break
                if line.strip().startswith("-"):
                    ideas.append(line.strip("- ").strip())
        return ideas

    def parse_releases(self) -> List[Dict[str, str]]:
        """Parse docs/CHANGELOG.md for release nodes."""
        changelog = Path(self.repo_path) / "docs" / "CHANGELOG.md"
        if not changelog.exists():
            return []
        text = changelog.read_text(encoding="utf-8")
        releases: List[Dict[str, str]] = []
        pattern = re.compile(r"\[(\d+\.\d+\.\d+)\]\s*-\s*(\d{4}-\d{2}-\d{2})")
        for version, date in pattern.findall(text):
            releases.append({"version": version, "date": date})
        return releases

    def parse_libraries(self) -> List[str]:
        libs: List[str] = []
        req = Path(self.repo_path) / "requirements.txt"
        if req.exists():
            for line in req.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    libs.append(line.split("==")[0])
        pkg = Path(self.repo_path) / "package.json"
        if pkg.exists():
            content = pkg.read_text()
            for match in re.findall(r'"([\w-]+)"\s*:\s*"', content):
                libs.append(match)
        return libs

    # --- Git Parsing ---
    def parse_commits(self) -> Iterable[Dict[str, str]]:
        """Yield commits from the repository with requirement references."""
        branch = self.repo.heads['development'] if 'development' in self.repo.heads else self.repo.head.commit
        for commit in self.repo.iter_commits(branch):
            message = self._sanitize_message(commit.message)
            req_ids = REQ_PATTERN.findall(message)
            files = list(commit.stats.files.keys())
            libraries = self._detect_library_changes(commit)
            attempt = self._detect_attempt(commit)
            yield {
                "hash": commit.hexsha,
                "message": message,
                "author": commit.author.email,
                "date": commit.committed_datetime.isoformat(),
                "files": files,
                "requirements": req_ids,
                "libraries": libraries,
                "attempt": attempt,
            }

    # --- Helpers for commit parsing ---
    @staticmethod
    def _sanitize_message(message: str) -> str:
        """Remove suspicious long tokens from commit messages."""
        return re.sub(r"[A-Za-z0-9]{32,}", "<redacted>", message)

    def _detect_library_changes(self, commit) -> List[Tuple[str, str]]:
        """Return list of (library, action) tuples detected in this commit."""
        libs: List[Tuple[str, str]] = []
        if not commit.parents:
            return libs
        diff = commit.diff(commit.parents[0], paths=["requirements.txt", "package.json"])
        for d in diff:
            # Handle both string and bytes diff formats
            if isinstance(d.diff, bytes):
                diff_lines = d.diff.decode("utf-8", errors="ignore").splitlines()
            else:
                diff_lines = str(d.diff).splitlines()
            
            for line in diff_lines:
                if line.startswith("+"):
                    lib = self._parse_library_line(line[1:], d.b_path)
                    if lib:
                        libs.append((lib, "added"))
                elif line.startswith("-"):
                    lib = self._parse_library_line(line[1:], d.a_path)
                    if lib:
                        libs.append((lib, "removed"))
        return libs

    @staticmethod
    def _parse_library_line(line: str, path: str) -> Optional[str]:
        line = line.strip()
        if path.endswith("requirements.txt"):
            if line and not line.startswith("#"):
                return line.split("==")[0]
        if path.endswith("package.json"):
            m = re.search(r'"([\w-]+)"\s*:', line)
            if m:
                return m.group(1)
        return None

    @staticmethod
    def _detect_attempt(commit) -> Optional[str]:
        msg = commit.message.lower()
        if any(k in msg for k in ["wip", "spike", "attempt"]):
            return commit.hexsha
        return None

    # --- Neo4j Insertion ---
    def ingest(self) -> None:
        sprints = self.parse_sprints()
        releases = self.parse_releases()
        libraries = self.parse_libraries()
        with self.driver.session() as session:
            session.execute_write(self._create_constraints)
            for s in sprints:
                session.execute_write(self._merge_sprint, s)
                reqs = self.extract_requirements(s.get("prd"))
                for r in reqs:
                    session.execute_write(self._merge_requirement, r, s["number"])
                for idea in self.extract_ideas(s.get("prd")):
                    session.execute_write(self._merge_idea, idea, s["number"])
            for rel in releases:
                session.execute_write(self._merge_release, rel)
            for lib in libraries:
                session.execute_write(self._merge_library, lib)
            for commit in self.parse_commits():
                session.execute_write(self._merge_commit, commit)

    # Constraint helpers
    @staticmethod
    def _create_constraints(tx):
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sprint) REQUIRE s.number IS UNIQUE")
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE")
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:GitCommit) REQUIRE c.hash IS UNIQUE")
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE")
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (rel:Release) REQUIRE rel.version IS UNIQUE")
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (lib:Library) REQUIRE lib.name IS UNIQUE")

    @staticmethod
    def _merge_sprint(tx, sprint: Dict[str, str]):
        tx.run(
            "MERGE (s:Sprint {number: $number}) SET s.path=$path",
            number=sprint["number"], path=sprint["path"]
        )

    @staticmethod
    def _merge_requirement(tx, req: Dict[str, str], sprint_number: str):
        tx.run(
            "MERGE (r:Requirement {id:$id}) SET r.description=$desc "
            "WITH r MATCH (s:Sprint {number:$sprint}) "
            "MERGE (r)-[:PART_OF]->(s)",
            id=req["id"], desc=req["description"], sprint=sprint_number
        )

    @staticmethod
    def _merge_commit(tx, commit: Dict[str, str]):
        # Unified temporal schema: GitCommit + TOUCHED with timestamp
        tx.run(
            "MERGE (c:GitCommit {hash:$hash}) SET c.message=$msg, c.timestamp=$ts",
            hash=commit["hash"], msg=commit["message"], ts=commit.get("date")
        )
        for path in commit["files"]:
            tx.run(
                "MERGE (f:File {path:$path})"
                " WITH f MATCH (c:GitCommit {hash:$hash})"
                " MERGE (c)-[r:TOUCHED]->(f)"
                " ON CREATE SET r.timestamp=$ts",
                path=path, hash=commit["hash"], ts=commit.get("date")
            )
        for rid in commit["requirements"]:
            tx.run(
                "MATCH (r:Requirement {id:$rid}), (c:GitCommit {hash:$hash}) "
                "MERGE (c)-[:IMPLEMENTS]->(r)",
                rid=rid, hash=commit["hash"]
            )
        for lib, action in commit.get("libraries", []):
            tx.run(
                "MERGE (l:Library {name:$name})"
                " WITH l MATCH (c:GitCommit {hash:$hash})"
                " MERGE (c)-[:USES {action:$action}]->(l)",
                name=lib,
                hash=commit["hash"],
                action=action,
            )
        if commit.get("attempt"):
            tx.run(
                "MERGE (a:Attempt {id:$id})"
                " WITH a MATCH (c:GitCommit {hash:$hash})"
                " MERGE (c)-[:PROTOTYPED_IN]->(a)",
                id=commit["attempt"],
                hash=commit["hash"],
            )

    @staticmethod
    def _merge_release(tx, rel: Dict[str, str]):
        tx.run(
            "MERGE (r:Release {version:$version}) SET r.date=$date",
            version=rel["version"],
            date=rel["date"],
        )

    @staticmethod
    def _merge_library(tx, name: str):
        tx.run("MERGE (l:Library {name:$name})", name=name)

    @staticmethod
    def _merge_idea(tx, idea: str, sprint_number: str):
        tx.run(
            "MERGE (i:Idea {description:$desc})"
            "WITH i MATCH (s:Sprint {number:$sprint})"
            "MERGE (i)-[:PART_OF]->(s)",
            desc=idea,
            sprint=sprint_number,
        )


def main():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "password")
    repo = Path(__file__).resolve().parents[1]
    ingester = DevGraphIngester(str(repo), uri, user, password)
    ingester.ingest()


if __name__ == "__main__":
    main()
