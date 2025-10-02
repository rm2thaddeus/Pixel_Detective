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

    def _normalize_repo_relative_path(self, file_path: Path) -> str:
        """Return repo-relative POSIX path for a given path.

        Ensures consistent forward-slash paths relative to the repository root
        regardless of OS or whether an absolute/relative path was provided.
        """
        try:
            root = Path(self.repo_path).resolve()
            p = file_path
            if not p.is_absolute():
                p = (root / p).resolve()
            rel = p.relative_to(root)
            return rel.as_posix()
        except Exception:
            # Fallback: best-effort POSIX-ify the original path
            return str(file_path).replace('\\', '/')

    def ingest(self):
        """Main ingestion process with enhanced coverage."""
        print("Starting enhanced ingestion...")

        # Parse all available data
        sprints = self.parse_all_sprints()
        requirements = self.extract_all_requirements()
        documents = self.parse_documents()
        chunks = self.parse_chunks()
        cross_references = self.find_cross_references()

        print(
            f"Found {len(sprints)} sprints, {len(requirements)} requirements, {len(documents)} documents, {len(chunks)} chunks"
        )

        with self.driver.session() as session:
            # Create constraints
            session.execute_write(self._create_constraints)

            # BATCH OPERATIONS - Phase 0 Performance Fix
            print("Creating nodes in batches...")
            session.execute_write(self._batch_create_sprints, sprints)
            session.execute_write(self._batch_create_requirements, requirements)
            session.execute_write(self._batch_create_documents, documents)
            session.execute_write(self._batch_create_chunks, chunks)

            # BATCH RELATIONSHIPS - Phase 0 Performance Fix
            print("Creating relationships in batches...")
            
            # Prepare relationship data
            req_sprint_rels = [{'req_id': req['id'], 'sprint_num': req['sprint_number']} 
                             for req in requirements if req.get('sprint_number')]
            
            sprint_doc_rels = [{'sprint_num': self._infer_sprint_number_from_path(doc.get('path')), 'doc_path': doc['path']} 
                             for doc in documents if self._infer_sprint_number_from_path(doc.get('path'))]
            
            doc_chunk_rels = [{'doc_path': ch['doc_path'], 'chunk_id': ch['id']} for ch in chunks]
            
            chunk_req_rels = [{'chunk_id': ch['id'], 'req_id': rid} 
                            for ch in chunks for rid in ch.get('mentions', []) or []]
            
            doc_ref_rels = [{'doc_path': doc['path'], 'ref': ref} 
                          for doc in documents for ref in doc.get('references', [])]

            # Execute batch relationship creation
            if req_sprint_rels:
                session.execute_write(self._batch_create_requirement_sprint_rels, req_sprint_rels)
            if sprint_doc_rels:
                session.execute_write(self._batch_create_sprint_doc_rels, sprint_doc_rels)
            if doc_chunk_rels:
                session.execute_write(self._batch_create_doc_chunk_rels, doc_chunk_rels)
            if chunk_req_rels:
                session.execute_write(self._batch_create_chunk_req_rels, chunk_req_rels)
            if doc_ref_rels:
                session.execute_write(self._batch_create_doc_ref_rels, doc_ref_rels)
            
            # Create cross-sprint relationships (keep individual for now due to complexity)
            for ref in cross_references:
                session.execute_write(self._merge_cross_reference, ref)
            
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
        
        # Process docs/sprints directory
        base = Path(self.repo_path) / "docs" / "sprints"
        if base.exists():
            for item in base.iterdir():
                if item.is_dir():
                    for file_path in item.rglob("*.md"):
                        if file_path.is_file():
                            doc = self._parse_document_file(file_path)
                            if doc:
                                documents.append(doc)
        
        # Process root-level .md files
        root_path = Path(self.repo_path)
        for file_path in root_path.glob("*.md"):
            if file_path.is_file():
                doc = self._parse_document_file(file_path)
                if doc:
                    documents.append(doc)
        
        # Process docs directory (non-sprints)
        docs_path = Path(self.repo_path) / "docs"
        if docs_path.exists():
            for file_path in docs_path.rglob("*.md"):
                if file_path.is_file() and not str(file_path).startswith(str(base)):
                    doc = self._parse_document_file(file_path)
                    if doc:
                        documents.append(doc)
        
        return documents

    def _parse_document_file(self, file_path: Path) -> Optional[Dict[str, str]]:
        """Parse a single document file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Extract title from first H1 heading or filename
            title = self._extract_title(content, file_path.name)
            
            # Extract references to other documents, requirements, sprints
            references = []
            
            # Find sprint references
            for match in SPRINT_REF_PATTERN.finditer(content):
                references.append(f"sprint-{match.group(1)}")
            
            # Find requirement references
            for match in REQ_REF_PATTERN.finditer(content):
                references.append(f"{match.group(0)}")
            
            return {
                "path": self._normalize_repo_relative_path(file_path),
                "name": file_path.name,
                "title": title,
                # Use content_preview to match batch upsert expectations
                "content_preview": content[:500],
                "references": list(set(references)),
                "type": "document"
            }
        except Exception as e:
            print(f"Error parsing document {file_path}: {e}")
            return None
    
    def _extract_title(self, content: str, filename: str) -> str:
        """Extract title from markdown content or use filename."""
        lines = content.split('\n')
        for line in lines:
            # Look for first H1 heading
            if line.strip().startswith('# '):
                return line.strip()[2:].strip()
            # Look for H2 heading if no H1
            elif line.strip().startswith('## ') and not any(l.strip().startswith('# ') for l in lines[:lines.index(line)]):
                return line.strip()[3:].strip()
        
        # Fallback to filename without extension
        return Path(filename).stem.replace('_', ' ').replace('-', ' ').title()

    # -------------------- Chunk Parsing --------------------
    def parse_chunks(self) -> List[Dict[str, object]]:
        """Parse Markdown documents into Chunk nodes by headings.

        Chunk identity: f"{path}#{slug}-{ordinal}" where slug is derived from heading text.
        """
        chunks: List[Dict[str, object]] = []
        
        # Process docs/sprints directory
        base = Path(self.repo_path) / "docs" / "sprints"
        if base.exists():
            for item in base.iterdir():
                if not item.is_dir():
                    continue
                for file_path in item.rglob("*.md"):
                    try:
                        text = file_path.read_text(encoding="utf-8")
                    except Exception:
                        continue
                    norm = self._normalize_repo_relative_path(file_path)
                    chunks.extend(self._extract_chunks_from_text(norm, text))
        
        # Process root-level .md files
        root_path = Path(self.repo_path)
        for file_path in root_path.glob("*.md"):
            try:
                text = file_path.read_text(encoding="utf-8")
                norm = self._normalize_repo_relative_path(file_path)
                chunks.extend(self._extract_chunks_from_text(norm, text))
            except Exception:
                continue
        
        # Process docs directory (non-sprints)
        docs_path = Path(self.repo_path) / "docs"
        if docs_path.exists():
            for file_path in docs_path.rglob("*.md"):
                if file_path.is_file() and not str(file_path).startswith(str(base)):
                    try:
                        text = file_path.read_text(encoding="utf-8")
                        norm = self._normalize_repo_relative_path(file_path)
                        chunks.extend(self._extract_chunks_from_text(norm, text))
                    except Exception:
                        continue
        
        return chunks

    @staticmethod
    def _slugify(text: str) -> str:
        t = re.sub(r"[^a-zA-Z0-9\s-]", "", text.strip().lower())
        t = re.sub(r"\s+", "-", t)
        t = re.sub(r"-+", "-", t)
        return t or "section"

    def _extract_chunks_from_text(self, path: str, text: str) -> List[Dict[str, object]]:
        lines = text.splitlines()
        chunks: List[Dict[str, object]] = []
        current: Optional[Dict[str, object]] = None
        ordinals = {2: 0, 3: 0, 1: 0}
        buffer: List[str] = []

        def flush():
            nonlocal current, buffer
            if current is not None:
                content = "\n".join(buffer).strip()
                # Mentions of requirements inside the chunk
                mentions = list({m.group(0) for m in REQ_REF_PATTERN.finditer(content)})
                current['content_preview'] = content[:400]
                # Store chunk text for downstream linkers (document_code_linker)
                # Keep bounded to avoid oversized properties
                current['text'] = content[:4000]
                current['length'] = len(content)
                current['mentions'] = mentions
                chunks.append(current)
            current = None
            buffer = []

        for line in lines:
            m = re.match(r"^(#{1,3})\s+(.*)$", line)
            if m:
                # Start of a new chunk at H1/H2/H3, flush previous
                flush()
                level = len(m.group(1))
                heading = m.group(2).strip()
                ordinals[level] = ordinals.get(level, 0) + 1
                slug = self._slugify(heading)
                cid = f"{path}#{slug}-{ordinals[level]:02d}"
                current = {
                    'id': cid,
                    'doc_path': path,
                    'heading': heading,
                    'level': level,
                    'ordinal': ordinals[level],
                    # Mark as documentation chunk for UI/type filters
                    'kind': 'doc',
                }
            else:
                buffer.append(line)
        flush()
        return chunks

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
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE")

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
    def _merge_chunk(tx, ch: Dict[str, object]):
        """Merge chunk node."""
        tx.run(
            "MERGE (c:Chunk {id: $id}) SET c += $props",
            id=ch['id'],
            props={k: v for k, v in ch.items() if k != 'id'}
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

    @staticmethod
    def _merge_sprint_contains_doc(tx, sprint_number: str, doc_path: str):
        """Create CONTAINS_DOC: (Sprint)-[:CONTAINS_DOC]->(Document)."""
        tx.run(
            "MATCH (s:Sprint {number: $num}), (d:Document {path: $path}) "
            "MERGE (s)-[:CONTAINS_DOC]->(d)",
            num=sprint_number, path=doc_path
        )

    @staticmethod
    def _merge_document_contains_chunk(tx, doc_path: str, chunk_id: str):
        """Create CONTAINS_CHUNK: (Document)-[:CONTAINS_CHUNK]->(Chunk)."""
        tx.run(
            "MATCH (d:Document {path: $path}), (c:Chunk {id: $cid}) "
            "MERGE (d)-[:CONTAINS_CHUNK]->(c)",
            path=doc_path, cid=chunk_id
        )

    @staticmethod
    def _merge_chunk_mentions_requirement(tx, chunk_id: str, req_id: str):
        """Create MENTIONS: (Chunk)-[:MENTIONS]->(Requirement)."""
        tx.run(
            "MATCH (c:Chunk {id: $cid}), (r:Requirement {id: $rid}) "
            "MERGE (c)-[:MENTIONS]->(r)",
            cid=chunk_id, rid=req_id
        )

    @staticmethod
    def _infer_sprint_number_from_path(path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        m = re.search(r"/sprint-(\d+)/", path.replace("\\", "/"))
        if m:
            return m.group(1)
        m2 = re.search(r"/s-(\d+)/", path.replace("\\", "/"))
        if m2:
            return m2.group(1)
        return None

    # BATCH OPERATIONS - Phase 0 Performance Fix
    @staticmethod
    def _batch_create_sprints(tx, sprints: List[Dict[str, str]]):
        """Batch create sprint nodes using UNWIND."""
        if not sprints:
            return
        tx.run("""
            UNWIND $sprints AS sprint
            MERGE (s:Sprint {number: sprint.number})
            SET s.name = sprint.name, 
                s.start_date = sprint.start_date, 
                s.end_date = sprint.end_date,
                s.uid = sprint.number
        """, sprints=sprints)

    @staticmethod
    def _batch_create_requirements(tx, requirements: List[Dict[str, str]]):
        """Batch create requirement nodes using UNWIND."""
        if not requirements:
            return
        tx.run("""
            UNWIND $requirements AS req
            MERGE (r:Requirement {id: req.id})
            SET r.title = req.title,
                r.description = req.description,
                r.author = req.author,
                r.date_created = req.date_created,
                r.tags = req.tags,
                r.sprint_number = req.sprint_number,
                r.uid = req.id
        """, requirements=requirements)

    @staticmethod
    def _batch_create_documents(tx, documents: List[Dict[str, str]]):
        """Batch create document nodes using UNWIND."""
        if not documents:
            return
        tx.run("""
            UNWIND $documents AS doc
            MERGE (d:Document {path: doc.path})
            SET d.name = doc.name,
                d.content_preview = doc.content_preview,
                d.references = doc.references,
                d.uid = doc.path
        """, documents=documents)

    @staticmethod
    def _batch_create_chunks(tx, chunks: List[Dict[str, str]]):
        """Batch create chunk nodes using UNWIND."""
        if not chunks:
            return
        tx.run("""
            UNWIND $chunks AS chunk
            MERGE (c:Chunk {id: chunk.id})
            SET c.doc_path = chunk.doc_path,
                c.heading = chunk.heading,
                c.level = chunk.level,
                c.ordinal = chunk.ordinal,
                c.content_preview = chunk.content_preview,
                c.length = chunk.length,
                c.mentions = chunk.mentions,
                c.uid = chunk.id
        """, chunks=chunks)

    @staticmethod
    def _batch_create_requirement_sprint_rels(tx, relationships: List[Dict[str, str]]):
        """Batch create PART_OF relationships between requirements and sprints."""
        if not relationships:
            return
        tx.run("""
            UNWIND $relationships AS rel
            MATCH (r:Requirement {id: rel.req_id}), (s:Sprint {number: rel.sprint_num})
            MERGE (r)-[:PART_OF]->(s)
        """, relationships=relationships)

    @staticmethod
    def _batch_create_sprint_doc_rels(tx, relationships: List[Dict[str, str]]):
        """Batch create CONTAINS_DOC relationships between sprints and documents."""
        if not relationships:
            return
        tx.run("""
            UNWIND $relationships AS rel
            MATCH (s:Sprint {number: rel.sprint_num}), (d:Document {path: rel.doc_path})
            MERGE (s)-[:CONTAINS_DOC]->(d)
        """, relationships=relationships)

    @staticmethod
    def _batch_create_doc_chunk_rels(tx, relationships: List[Dict[str, str]]):
        """Batch create CONTAINS_CHUNK relationships between documents and chunks."""
        if not relationships:
            return
        tx.run("""
            UNWIND $relationships AS rel
            MATCH (d:Document {path: rel.doc_path}), (c:Chunk {id: rel.chunk_id})
            MERGE (d)-[:CONTAINS_CHUNK]->(c)
        """, relationships=relationships)

    @staticmethod
    def _batch_create_chunk_req_rels(tx, relationships: List[Dict[str, str]]):
        """Batch create MENTIONS relationships between chunks and requirements."""
        if not relationships:
            return
        tx.run("""
            UNWIND $relationships AS rel
            MATCH (c:Chunk {id: rel.chunk_id}), (r:Requirement {id: rel.req_id})
            MERGE (c)-[:MENTIONS]->(r)
        """, relationships=relationships)

    @staticmethod
    def _batch_create_doc_ref_rels(tx, relationships: List[Dict[str, str]]):
        """Batch create REFERENCES relationships between documents and other entities."""
        if not relationships:
            return
        tx.run("""
            UNWIND $relationships AS rel
            MATCH (d:Document {path: rel.doc_path})
            WITH d, rel
            WHERE rel.ref STARTS WITH 'sprint-'
            // rel.ref is like "sprint-12"; extract the numeric part for Sprint.number
            MERGE (s:Sprint {number: replace(rel.ref, 'sprint-', '')})
            MERGE (d)-[:REFERENCES]->(s)
        """, relationships=relationships)
        
        # Handle requirement references
        tx.run("""
            UNWIND $relationships AS rel
            MATCH (d:Document {path: rel.doc_path})
            WITH d, rel
            WHERE rel.ref STARTS WITH 'FR-' OR rel.ref STARTS WITH 'NFR-'
            MATCH (r:Requirement {id: rel.ref})
            MERGE (d)-[:REFERENCES]->(r)
        """, relationships=relationships)


def main():
    """Main entry point."""
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "password")
    repo = os.environ.get("REPO_PATH", str(Path(__file__).resolve().parents[1]))
    
    ingester = EnhancedDevGraphIngester(str(repo), uri, user, password)
    ingester.ingest()


if __name__ == "__main__":
    main()
