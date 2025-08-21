#!/usr/bin/env python3
"""Simple Enhanced Developer Graph Ingestion - Focus on Meaningful Data.

This version:
- Only creates nodes with clear, meaningful IDs
- Creates more relationship types
- Avoids hash-based IDs for unclear data
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from git import Repo
from neo4j import GraphDatabase


REQ_PATTERN = re.compile(r"\b(?:FR|NFR)-\d{2}-\d{2}\b")
SPRINT_REF_PATTERN = re.compile(r"\b(?:sprint|Sprint)-(\d+)\b")


class SimpleEnhancedIngester:
    """Simple enhanced parser focusing on meaningful data."""

    def __init__(self, repo_path: str, neo4j_uri: str, user: str, password: str):
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))

    def ingest(self):
        """Main ingestion process."""
        print("Starting simple enhanced ingestion...")
        
        # Clear existing data first
        with self.driver.session() as session:
            session.execute_write(self._clear_existing_data)
        
        # Parse data
        sprints = self.parse_sprints()
        requirements = self.extract_requirements()
        documents = self.parse_documents()
        
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
            
            # Create document relationships
            for doc in documents:
                if doc.get('references'):
                    for ref in doc['references']:
                        session.execute_write(self._merge_document_reference, doc['path'], ref)
            
            # Create cross-sprint relationships for related requirements
            self.create_cross_sprint_relationships(session)
            
            print("Simple enhanced ingestion completed!")

    def parse_sprints(self) -> List[Dict[str, str]]:
        """Parse all sprint directories."""
        base = Path(self.repo_path) / "docs" / "sprints"
        sprints = []
        
        for item in base.iterdir():
            if item.is_dir():
                if item.name.startswith("sprint-"):
                    num = item.name.split("-")[1]
                    sprints.append({
                        "number": num,
                        "path": str(item),
                        "name": f"sprint-{num}",
                        "type": "sprint"
                    })
                elif item.name.startswith("s-"):
                    num = item.name.split("-")[1]
                    sprints.append({
                        "number": num,
                        "path": str(item),
                        "name": f"s-{num}",
                        "type": "sprint"
                    })
                elif item.name in ["critical-ui-refactor", "planning"]:
                    sprints.append({
                        "number": "special",
                        "path": str(item),
                        "name": item.name,
                        "type": "special"
                    })
        
        return sprints

    def extract_requirements(self) -> List[Dict[str, str]]:
        """Extract requirements from PRD and README files."""
        requirements = []
        base = Path(self.repo_path) / "docs" / "sprints"
        
        for item in base.iterdir():
            if item.is_dir():
                sprint_num = None
                if item.name.startswith("sprint-"):
                    sprint_num = item.name.split("-")[1]
                elif item.name.startswith("s-"):
                    sprint_num = item.name.split("-")[1]
                elif item.name in ["critical-ui-refactor", "planning"]:
                    sprint_num = "special"
                
                if sprint_num:
                    # Check PRD files
                    prd = item / "PRD.md"
                    if prd.exists():
                        reqs = self.extract_requirements_from_file(prd, sprint_num)
                        requirements.extend(reqs)
                    
                    # Check README files
                    readme = item / "README.md"
                    if readme.exists():
                        reqs = self.extract_requirements_from_file(readme, sprint_num)
                        requirements.extend(reqs)
        
        return requirements

    def extract_requirements_from_file(self, file_path: Path, sprint_num: str) -> List[Dict[str, str]]:
        """Extract requirements from a markdown file."""
        reqs = []
        try:
            text = file_path.read_text(encoding="utf-8")
            
            # Look for FR/NFR patterns
            for line in text.splitlines():
                match = REQ_PATTERN.search(line)
                if match:
                    req_id = match.group()
                    description = line.replace(match.group(), "").strip()
                    if description.startswith(":"):
                        description = description[1:].strip()
                    
                    reqs.append({
                        "id": req_id,
                        "description": description,
                        "sprint_number": sprint_num,
                        "source_file": str(file_path),
                        "type": "requirement"
                    })
            
            # Look for other meaningful patterns
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("-") and len(line) > 10:
                    # Only create nodes for substantial content
                    if any(keyword in line.lower() for keyword in ["goal", "objective", "feature", "requirement", "milestone"]):
                        reqs.append({
                            "id": f"goal-{sprint_num}-{len(reqs):02d}",
                            "description": line.strip("- ").strip(),
                            "sprint_number": sprint_num,
                            "source_file": str(file_path),
                            "type": "goal"
                        })
                        
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        
        return reqs

    def parse_documents(self) -> List[Dict[str, str]]:
        """Parse document files for references."""
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
            
            # Extract references
            references = []
            
            # Find sprint references
            for match in SPRINT_REF_PATTERN.finditer(content):
                references.append(f"sprint-{match.group(1)}")
            
            # Find requirement references
            for match in REQ_PATTERN.finditer(content):
                references.append(match.group())
            
            # Only create document nodes if they have meaningful references
            if references:
                return {
                    "path": str(file_path),
                    "name": file_path.name,
                    "references": list(set(references)),
                    "type": "document"
                }
        
        except Exception as e:
            print(f"Error parsing document {file_path}: {e}")
        
        return None

    def create_cross_sprint_relationships(self, session):
        """Create relationships between related requirements across sprints."""
        with session.begin_transaction() as tx:
            # EVOLVES_FROM: same requirement suffix across different sprints
            result = tx.run(
                """
                MATCH (r1:Requirement), (r2:Requirement)
                WHERE r1.id <> r2.id
                  AND split(r1.id, "-")[2] = split(r2.id, "-")[2]  // same XX suffix
                  AND split(r1.id, "-")[1] < split(r2.id, "-")[1]  // earlier sprint to later sprint
                WITH r1, r2 ORDER BY split(r1.id, "-")[1]
                MERGE (r2)-[:EVOLVES_FROM]->(r1)
                RETURN count(*) as count
                """
            )
            count = result.single()["count"]
            print(f"Created {count} EVOLVES_FROM relationships")

            # DEPENDS_ON: naive heuristic from descriptions
            result = tx.run(
                """
                MATCH (r1:Requirement), (r2:Requirement)
                WHERE r1.id <> r2.id AND toLower(r1.description) CONTAINS toLower(r2.id)
                MERGE (r1)-[:DEPENDS_ON]->(r2)
                RETURN count(*) as count
                """
            )
            count = result.single()["count"]
            print(f"Created {count} DEPENDS_ON relationships")

    @staticmethod
    def _clear_existing_data(tx):
        """Clear existing data to start fresh."""
        tx.run("MATCH (n) DETACH DELETE n")
        print("Cleared existing data")

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
    
    ingester = SimpleEnhancedIngester(str(repo), uri, user, password)
    ingester.ingest()


if __name__ == "__main__":
    main()
