#!/usr/bin/env python3
"""Enhanced Developer Graph Ingestion with Comprehensive Coverage.

This enhanced version covers:
- All sprint-related directories (sprint-*, s-*, critical-*)
- Cross-sprint requirement relationships
- Document dependencies and references
- More comprehensive relationship types
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Iterable, Optional, Tuple
from collections import defaultdict

from git import Repo
from neo4j import GraphDatabase


REQ_PATTERN = re.compile(r"\b(?:FR|NFR)-\d{2}-\d{2}\b")
SPRINT_REF_PATTERN = re.compile(r"\b(?:sprint|Sprint)-(\d+)\b")
REQ_REF_PATTERN = re.compile(r"\b(?:FR|NFR)-(\d{2})-(\d{2})\b")


class EnhancedDevGraphIngester:
    """Enhanced parser for comprehensive Developer Graph coverage."""

    def __init__(self, repo_path: str, neo4j_uri: str, user: str, password: str):
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
        self.requirement_map = {}  # Track requirements across sprints

    def ingest(self):
        """Main ingestion process with enhanced coverage."""
        print("Starting enhanced ingestion...")
        
        # Parse all available data
        sprints = self.parse_all_sprints()
        requirements = self.extract_all_requirements()
        documents = self.parse_documents()
        cross_references = self.find_cross_references()
        
        print(f"Found {len(sprints)} sprints, {len(requirements)} requirements, {len(documents)} documents")
        
        with self.driver.session() as session:
            # Create constraints
            session.execute_write(self._create_constraints)
            
            # Create nodes
            for sprint in sprints:
                session.execute_write(self._merge_sprint, sprint)
            
            for req in requirements:
                session.execute_write(self._merge_requirement, req)
            
            for doc in documents:
                session.execute_write(self._merge_document, doc)
            
            # Create relationships
            for req in requirements:
                if req.get('sprint_number'):
                    session.execute_write(self._merge_requirement_sprint, req['id'], req['sprint_number'])
            
            # Create cross-sprint relationships
            for ref in cross_references:
                session.execute_write(self._merge_cross_reference, ref)
            
            # Create document relationships
            for doc in documents:
                if doc.get('references'):
                    for ref in doc['references']:
                        session.execute_write(self._merge_document_reference, doc['path'], ref)
            
            print("Enhanced ingestion completed!")

    def parse_all_sprints(self) -> List[Dict[str, str]]:
        """Parse all sprint-related directories."""
        base = Path(self.repo_path) / "docs" / "sprints"
        sprints = []
        
        # Parse sprint status
        status_file = base / "planning" / "SPRINT_STATUS.md"
        status_map = self._parse_sprint_status(status_file)
        
        # Process all directories
        for item in base.iterdir():
            if item.is_dir():
                if item.name.startswith("sprint-"):
                    # Standard sprint directory
                    num = item.name.split("-")[1]
                    sprints.append(self._parse_sprint_directory(item, num, status_map))
                elif item.name.startswith("s-"):
                    # Alternative sprint naming
                    num = item.name.split("-")[1]
                    sprints.append(self._parse_sprint_directory(item, num, status_map, alt_name=item.name))
                elif item.name.startswith("critical-") or item.name.startswith("planning"):
                    # Special directories
                    sprints.append(self._parse_special_directory(item, status_map))
        
        return sprints

    def _parse_sprint_directory(self, path: Path, number: str, status_map: Dict[str, str], alt_name: str = None) -> Dict[str, str]:
        """Parse a sprint directory."""
        prd = path / "PRD.md"
        readme = path / "README.md"
        mindmap = path / "mindmap.md"
        
        return {
            "number": number,
            "path": str(path),
            "name": alt_name or f"sprint-{number}",
            "prd": str(prd) if prd.exists() else None,
            "readme": str(readme) if readme.exists() else None,
            "mindmap": str(mindmap) if mindmap.exists() else None,
            "status": status_map.get(number, "unknown"),
            "type": "sprint"
        }

    def _parse_special_directory(self, path: Path, status_map: Dict[str, str]) -> Dict[str, str]:
        """Parse special directories like critical-ui-refactor."""
        readme = path / "README.md"
        prd = path / "PRD.md"
        
        return {
            "number": "special",
            "path": str(path),
            "name": path.name,
            "prd": str(prd) if prd.exists() else None,
            "readme": str(readme) if readme.exists() else None,
            "status": "active",
            "type": "special"
        }

    def extract_all_requirements(self) -> List[Dict[str, str]]:
        """Extract all requirements from all documents."""
        requirements = []
        base = Path(self.repo_path) / "docs" / "sprints"
        
        for item in base.iterdir():
            if item.is_dir():
                # Check PRD files
                prd = item / "PRD.md"
                if prd.exists():
                    reqs = self.extract_requirements_from_file(prd)
                    for req in reqs:
                        req['sprint_number'] = item.name.split("-")[1] if item.name.startswith("sprint-") else "special"
                        req['source_file'] = str(prd)
                        requirements.append(req)
                
                # Check README files for additional requirements
                readme = item / "README.md"
                if readme.exists():
                    reqs = self.extract_requirements_from_file(readme)
                    for req in reqs:
                        req['sprint_number'] = item.name.split("-")[1] if item.name.startswith("sprint-") else "special"
                        req['source_file'] = str(readme)
                        requirements.append(req)
        
        return requirements

    def extract_requirements_from_file(self, file_path: Path) -> List[Dict[str, str]]:
        """Extract requirements from a markdown file."""
        reqs = []
        try:
            text = file_path.read_text(encoding="utf-8")
            
            # Look for FR/NFR patterns
            for line in text.splitlines():
                match = REQ_PATTERN.search(line)
                if match:
                    req_id = match.group()
                    # Extract description from the line
                    description = line.replace(match.group(), "").strip()
                    if description.startswith(":"):
                        description = description[1:].strip()
                    
                    reqs.append({
                        "id": req_id,
                        "description": description,
                        "raw": line.strip(),
                        "type": "requirement"
                    })
            
            # Look for other requirement-like patterns
            for line in text.splitlines():
                if line.strip().startswith("-") and ("requirement" in line.lower() or "goal" in line.lower()):
                    description = line.strip("- ").strip()
                    reqs.append({
                        "id": f"req-{len(reqs):03d}",
                        "description": description,
                        "raw": line.strip(),
                        "type": "goal"
                    })
                    
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        
        return reqs

    def parse_documents(self) -> List[Dict[str, str]]:
        """Parse all document files for references and content."""
        documents = []
        base = Path(self.repo_path) / "docs" / "sprints"
        
        for item in base.iterdir():
            if item.is_dir():
                for file_path in item.rglob("*.md"):
                    if file_path.is_file():
                        doc = self._parse_document_file(file_path)
                        if doc:
                            documents.append(doc)
        
        return documents

    def _parse_document_file(self, file_path: Path) -> Optional[Dict[str, str]]:
        """Parse a single document file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Extract references to other documents, requirements, sprints
            references = []
            
            # Find sprint references
            for match in SPRINT_REF_PATTERN.finditer(content):
                references.append(f"sprint-{match.group(1)}")
            
            # Find requirement references
            for match in REQ_REF_PATTERN.finditer(content):
                references.append(f"{match.group(0)}")
            
            return {
                "path": str(file_path),
                "name": file_path.name,
                "content": content[:500],  # First 500 chars
                "references": list(set(references)),
                "type": "document"
            }
        except Exception as e:
            print(f"Error parsing document {file_path}: {e}")
            return None

    def find_cross_references(self) -> List[Dict[str, str]]:
        """Find cross-references between requirements and sprints."""
        cross_refs = []
        
        # Look for requirements that reference other sprints
        for req in self.requirement_map.values():
            if 'references' in req:
                for ref in req['references']:
                    if ref.startswith('sprint-'):
                        cross_refs.append({
                            "from": req['id'],
                            "to": ref,
                            "type": "REFERENCES",
                            "description": f"{req['id']} references {ref}"
                        })
        
        return cross_refs

    def _parse_sprint_status(self, path: Path) -> Dict[str, str]:
        """Parse sprint status from planning document."""
        if not path.exists():
            return {}
        try:
            text = path.read_text(encoding="utf-8")
            status_map: Dict[str, str] = {}
            pattern = re.compile(r"Sprint\s+(\d+).*?Status\*\*:\s*\*\*(.*?)\*\*", re.S)
            for match in pattern.finditer(text):
                num, status = match.groups()
                status_map[num] = status.strip()
            return status_map
        except Exception as e:
            print(f"Error parsing sprint status: {e}")
            return {}

    # Neo4j operations
    @staticmethod
    def _create_constraints(tx):
        """Create database constraints."""
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sprint) REQUIRE s.number IS UNIQUE")
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE")
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.path IS UNIQUE")

    @staticmethod
    def _merge_sprint(tx, sprint: Dict[str, str]):
        """Merge sprint node."""
        tx.run(
            "MERGE (s:Sprint {number: $number}) SET s += $props",
            number=sprint["number"], 
            props={k: v for k, v in sprint.items() if k != "number"}
        )

    @staticmethod
    def _merge_requirement(tx, req: Dict[str, str]):
        """Merge requirement node."""
        tx.run(
            "MERGE (r:Requirement {id: $id}) SET r += $props",
            id=req["id"], 
            props={k: v for k, v in req.items() if k != "id"}
        )

    @staticmethod
    def _merge_document(tx, doc: Dict[str, str]):
        """Merge document node."""
        tx.run(
            "MERGE (d:Document {path: $path}) SET d += $props",
            path=doc["path"], 
            props={k: v for k, v in doc.items() if k != "path"}
        )

    @staticmethod
    def _merge_requirement_sprint(tx, req_id: str, sprint_number: str):
        """Create PART_OF relationship between requirement and sprint."""
        tx.run(
            "MATCH (r:Requirement {id: $req_id}), (s:Sprint {number: $sprint_number}) "
            "MERGE (r)-[:PART_OF]->(s)",
            req_id=req_id, sprint_number=sprint_number
        )

    @staticmethod
    def _merge_cross_reference(tx, ref: Dict[str, str]):
        """Create cross-reference relationship."""
        tx.run(
            "MATCH (a:Requirement {id: $from_id}), (b:Sprint {number: $to_id}) "
            "MERGE (a)-[:REFERENCES]->(b)",
            from_id=ref["from"], to_id=ref["to"].replace("sprint-", "")
        )

    @staticmethod
    def _merge_document_reference(tx, doc_path: str, ref: str):
        """Create document reference relationship."""
        if ref.startswith("sprint-"):
            tx.run(
                "MATCH (d:Document {path: $doc_path}), (s:Sprint {number: $sprint_num}) "
                "MERGE (d)-[:REFERENCES]->(s)",
                doc_path=doc_path, sprint_num=ref.replace("sprint-", "")
            )
        elif ref.startswith(("FR-", "NFR-")):
            tx.run(
                "MATCH (d:Document {path: $doc_path}), (r:Requirement {id: $req_id}) "
                "MERGE (d)-[:REFERENCES]->(r)",
                doc_path=doc_path, req_id=ref
            )


def main():
    """Main entry point."""
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "password")
    repo = Path(__file__).resolve().parents[1]
    
    ingester = EnhancedDevGraphIngester(str(repo), uri, user, password)
    ingester.ingest()


if __name__ == "__main__":
    main()
