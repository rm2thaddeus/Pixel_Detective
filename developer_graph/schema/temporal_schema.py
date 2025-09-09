"""Temporal Neo4j Schema Utilities

Phase 1: provide minimal schema helpers for GitCommit and File nodes, and
relationships that carry commit/timestamp metadata.
"""

from __future__ import annotations

from typing import Dict

from neo4j import Driver


def apply_schema(driver: Driver) -> None:
    """Create constraints and indexes required by the temporal semantic graph."""
    with driver.session() as session:
        # Core constraints
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:GitCommit) REQUIRE c.hash IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (ch:Chunk) REQUIRE ch.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.path IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sprint) REQUIRE s.number IS UNIQUE")
        
        # Phase 0: Directory hierarchy constraints
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (dir:Directory) REQUIRE dir.path IS UNIQUE")
        
        # Phase 1: Performance indexes for time-bounded queries
        session.run("CREATE INDEX IF NOT EXISTS FOR (c:GitCommit) ON (c.timestamp)")
        # Legacy index kept for compatibility in mixed graphs; prefer GitCommit
        session.run("CREATE INDEX IF NOT EXISTS FOR (c:Commit) ON (c.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.path)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (r:Requirement) ON (r.id)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (ch:Chunk) ON (ch.id)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.path)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (s:Sprint) ON (s.number)")
        
        # Phase 0: Directory hierarchy indexes
        session.run("CREATE INDEX IF NOT EXISTS FOR (dir:Directory) ON (dir.path)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (dir:Directory) ON (dir.depth)")
        
        # Relationship indexes for temporal queries
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:TOUCHED]-() ON (r.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:IMPLEMENTS]-() ON (r.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:EVOLVES_FROM]-() ON (r.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:REFACTORED_TO]-() ON (r.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:DEPRECATED_BY]-() ON (r.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:LINKS_TO]-() ON (r.timestamp)")
        
        # Phase 0: Directory hierarchy relationship indexes
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:CONTAINS]-() ON (r.timestamp)")

        # Phase 1: Vector index for semantic search on Chunk embeddings
        try:
            session.run("""
                CREATE VECTOR INDEX chunk_vec_idx IF NOT EXISTS
                FOR (ch:Chunk) ON (ch.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 512,
                    `vector.similarity_function`: 'cosine'
                }}
            """)
        except Exception as e:
            print(f"Warning: Could not create vector index: {e}")
            # Fallback: create a regular index on embedding property for now
            try:
                session.run("CREATE INDEX IF NOT EXISTS FOR (ch:Chunk) ON (ch.embedding)")
            except Exception:
                pass

        # Full-text indexes to accelerate search
        # Neo4j 4.x/5.x syntax; create indexes per label for clarity
        try:
            session.run("CREATE FULLTEXT INDEX file_fulltext IF NOT EXISTS FOR (f:File) ON EACH [f.path]")
        except Exception:
            pass
        try:
            session.run("CREATE FULLTEXT INDEX requirement_fulltext IF NOT EXISTS FOR (r:Requirement) ON EACH [r.id, r.title]")
        except Exception:
            pass
        try:
            session.run("CREATE FULLTEXT INDEX commit_fulltext IF NOT EXISTS FOR (c:GitCommit) ON EACH [c.message, c.author]")
        except Exception:
            pass
        try:
            session.run("CREATE FULLTEXT INDEX chunk_fulltext IF NOT EXISTS FOR (ch:Chunk) ON EACH [ch.text]")
        except Exception:
            pass
        try:
            session.run("CREATE FULLTEXT INDEX document_fulltext IF NOT EXISTS FOR (d:Document) ON EACH [d.path, d.title]")
        except Exception:
            pass


def merge_commit(tx, commit: Dict[str, object]):
    tx.run(
        """
        MERGE (c:GitCommit {hash: $hash})
        ON CREATE SET c.message = $message, c.author = $author, c.timestamp = $timestamp, c.branch = $branch, c.uid = $uid
        ON MATCH SET c.message = coalesce(c.message, $message),
                      c.uid = coalesce(c.uid, $uid)
        """,
        hash=commit["hash"],
        message=commit.get("message"),
        author=commit.get("author_email") or commit.get("author"),
        timestamp=commit.get("timestamp"),
        branch=commit.get("branch", "unknown"),
        uid=str(commit["hash"]) if "hash" in commit else None,
    )


def merge_file(tx, file_info: Dict[str, object]):
    tx.run(
        """
        MERGE (f:File {path: $path})
        ON CREATE SET f.language = $language, f.uid = $uid
        ON MATCH SET f.uid = coalesce(f.uid, $uid)
        """,
        path=file_info["path"],
        language=file_info.get("language"),
        uid=str(file_info["path"]) if "path" in file_info else None,
    )


def relate_commit_touched_file(tx, commit_hash: str, file_path: str, change_type: str, timestamp: str):
    tx.run(
        """
        MATCH (c:GitCommit {hash: $hash})
        MERGE (f:File {path: $path})
        MERGE (c)-[r:TOUCHED]->(f)
        ON CREATE SET r.change_type = $change_type, r.timestamp = $timestamp
        ON MATCH SET r.timestamp = coalesce(r.timestamp, $timestamp)
        """,
        hash=commit_hash,
        path=file_path,
        change_type=change_type,
        timestamp=timestamp,
    )


# -------------------- Phase 2: Enhanced Schema Helpers --------------------

def merge_requirement(tx, requirement: Dict[str, object]):
    """Merge a Requirement node.

    Expected keys: id, title, author, date_created (ISO), goal_alignment, tags
    """
    tx.run(
        """
        MERGE (r:Requirement {id: $id})
        ON CREATE SET r.title = $title,
                      r.author = $author,
                      r.date_created = $date_created,
                      r.goal_alignment = $goal_alignment,
                      r.tags = $tags,
                      r.uid = $uid
        ON MATCH SET r.title = coalesce($title, r.title),
                     r.goal_alignment = coalesce($goal_alignment, r.goal_alignment),
                     r.uid = coalesce(r.uid, $uid)
        """,
        id=requirement["id"],
        title=requirement.get("title"),
        author=requirement.get("author"),
        date_created=requirement.get("date_created"),
        goal_alignment=requirement.get("goal_alignment"),
        tags=requirement.get("tags"),
        uid=str(requirement["id"]) if "id" in requirement else None,
    )


def relate_implements(tx, requirement_id: str, file_path: str, commit_hash: str, timestamp: str):
    """Create IMPLEMENTS relationship with commit metadata."""
    tx.run(
        """
        MERGE (r:Requirement {id: $rid})
        MERGE (f:File {path: $path})
        MERGE (r)-[rel:IMPLEMENTS]->(f)
        ON CREATE SET rel.commit = $commit, rel.timestamp = $ts
        ON MATCH SET rel.commit = coalesce(rel.commit, $commit),
                      rel.timestamp = coalesce(rel.timestamp, $ts)
        """,
        rid=requirement_id,
        path=file_path,
        commit=commit_hash,
        ts=timestamp,
    )


def relate_evolves_from_requirement(
    tx,
    new_req_id: str,
    old_req_id: str,
    commit_hash: str,
    diff_summary: str | None = None,
    timestamp: str | None = None,
):
    """Create EVOLVES_FROM relationship between Requirement nodes.

    Optionally set a `timestamp` when available to enable time-bounded queries.
    """
    tx.run(
        """
        MERGE (n:Requirement {id: $new_id})
        MERGE (o:Requirement {id: $old_id})
        MERGE (n)-[rel:EVOLVES_FROM]->(o)
        ON CREATE SET rel.commit = $commit, rel.diff_summary = $diff, rel.timestamp = $ts
        ON MATCH SET rel.commit = coalesce(rel.commit, $commit),
                      rel.timestamp = coalesce(rel.timestamp, $ts)
        """,
        new_id=new_req_id,
        old_id=old_req_id,
        commit=commit_hash,
        diff=diff_summary,
        ts=timestamp,
    )


def relate_refactored_file(
    tx,
    old_path: str,
    new_path: str,
    commit_hash: str,
    refactor_type: str | None = None,
    timestamp: str | None = None,
):
    """Create REFACTORED_TO relationship between File nodes with commit metadata.

    Optionally set a `timestamp` when available to enable time-bounded queries.
    """
    tx.run(
        """
        MERGE (o:File {path: $old})
        MERGE (n:File {path: $new})
        MERGE (o)-[rel:REFACTORED_TO]->(n)
        ON CREATE SET rel.commit = $commit, rel.refactor_type = $rtype, rel.timestamp = $ts
        ON MATCH SET rel.commit = coalesce(rel.commit, $commit),
                      rel.timestamp = coalesce(rel.timestamp, $ts)
        """,
        old=old_path,
        new=new_path,
        commit=commit_hash,
        rtype=refactor_type,
        ts=timestamp,
    )


def relate_deprecated_by(
    tx,
    node_label: str,
    node_key: str,
    node_value: str,
    replacement_label: str,
    replacement_key: str,
    replacement_value: str,
    commit_hash: str,
    reason: str | None = None,
    timestamp: str | None = None,
):
    """Create DEPRECATED_BY relationship between arbitrary nodes with commit metadata.

    node_label/replacement_label should be labels like 'Requirement' or 'File'.
    Keys are property names (e.g., 'id' for Requirement, 'path' for File).
    """
    tx.run(
        f"""
        MERGE (n:{node_label} {{{node_key}: $nval}})
        MERGE (r:{replacement_label} {{{replacement_key}: $rval}})
        MERGE (n)-[rel:DEPRECATED_BY]->(r)
        ON CREATE SET rel.commit = $commit, rel.reason = $reason, rel.timestamp = $ts
        ON MATCH SET rel.commit = coalesce(rel.commit, $commit),
                      rel.timestamp = coalesce(rel.timestamp, $ts)
        """,
        nval=node_value,
        rval=replacement_value,
        commit=commit_hash,
        reason=reason,
        ts=timestamp,
    )


# -------------------- Phase 1: Temporal Semantic Graph Schema Helpers --------------------

def merge_document(tx, document: Dict[str, object]):
    """Merge a Document node for temporal semantic graph.
    
    Expected keys: path, title, type, uid
    """
    tx.run(
        """
        MERGE (d:Document {path: $path})
        ON CREATE SET d.title = $title,
                      d.type = $type,
                      d.uid = $uid
        ON MATCH SET d.title = coalesce($title, d.title),
                     d.type = coalesce($type, d.type),
                     d.uid = coalesce(d.uid, $uid)
        """,
        path=document["path"],
        title=document.get("title"),
        type=document.get("type"),
        uid=document.get("uid") or str(document["path"]),
    )


def merge_chunk(tx, chunk: Dict[str, object]):
    """Merge a Chunk node for temporal semantic graph.
    
    Expected keys: id, kind, heading, section, file_path, span, text, length, embedding, uid
    """
    tx.run(
        """
        MERGE (ch:Chunk {id: $id})
        ON CREATE SET ch.kind = $kind,
                      ch.heading = $heading,
                      ch.section = $section,
                      ch.file_path = $file_path,
                      ch.span = $span,
                      ch.text = $text,
                      ch.length = $length,
                      ch.embedding = $embedding,
                      ch.uid = $uid
        ON MATCH SET ch.kind = coalesce($kind, ch.kind),
                     ch.heading = coalesce($heading, ch.heading),
                     ch.section = coalesce($section, ch.section),
                     ch.file_path = coalesce($file_path, ch.file_path),
                     ch.span = coalesce($span, ch.span),
                     ch.text = coalesce($text, ch.text),
                     ch.length = coalesce($length, ch.length),
                     ch.embedding = coalesce($embedding, ch.embedding),
                     ch.uid = coalesce(ch.uid, $uid)
        """,
        id=chunk["id"],
        kind=chunk.get("kind"),
        heading=chunk.get("heading"),
        section=chunk.get("section"),
        file_path=chunk.get("file_path"),
        span=chunk.get("span"),
        text=chunk.get("text"),
        length=chunk.get("length"),
        embedding=chunk.get("embedding"),
        uid=chunk.get("uid") or str(chunk["id"]),
    )


def merge_sprint(tx, sprint: Dict[str, object]):
    """Merge a Sprint node for temporal semantic graph.
    
    Expected keys: number, name, start_date, end_date, uid
    """
    tx.run(
        """
        MERGE (s:Sprint {number: $number})
        ON CREATE SET s.name = $name,
                      s.start_date = $start_date,
                      s.end_date = $end_date,
                      s.uid = $uid
        ON MATCH SET s.name = coalesce($name, s.name),
                     s.start_date = coalesce($start_date, s.start_date),
                     s.end_date = coalesce($end_date, s.end_date),
                     s.uid = coalesce(s.uid, $uid)
        """,
        number=sprint["number"],
        name=sprint.get("name"),
        start_date=sprint.get("start_date"),
        end_date=sprint.get("end_date"),
        uid=sprint.get("uid") or f"sprint-{sprint['number']}",
    )


def relate_document_contains_chunk(tx, document_path: str, chunk_id: str):
    """Create CONTAINS_CHUNK relationship between Document and Chunk."""
    tx.run(
        """
        MATCH (d:Document {path: $doc_path})
        MATCH (ch:Chunk {id: $chunk_id})
        MERGE (d)-[:CONTAINS_CHUNK]->(ch)
        """,
        doc_path=document_path,
        chunk_id=chunk_id,
    )


def relate_chunk_part_of_file(tx, chunk_id: str, file_path: str):
    """Create PART_OF relationship between Chunk and File."""
    tx.run(
        """
        MATCH (ch:Chunk {id: $chunk_id})
        MATCH (f:File {path: $file_path})
        MERGE (ch)-[:PART_OF]->(f)
        """,
        chunk_id=chunk_id,
        file_path=file_path,
    )


def relate_sprint_includes_commit(tx, sprint_number: str, commit_hash: str):
    """Create INCLUDES relationship between Sprint and GitCommit."""
    tx.run(
        """
        MATCH (s:Sprint {number: $sprint_number})
        MATCH (c:GitCommit {hash: $commit_hash})
        MERGE (s)-[:INCLUDES]->(c)
        """,
        sprint_number=sprint_number,
        commit_hash=commit_hash,
    )


def relate_sprint_contains_doc(tx, sprint_number: str, document_path: str):
    """Create CONTAINS_DOC relationship between Sprint and Document."""
    tx.run(
        """
        MATCH (s:Sprint {number: $sprint_number})
        MATCH (d:Document {path: $doc_path})
        MERGE (s)-[:CONTAINS_DOC]->(d)
        """,
        sprint_number=sprint_number,
        doc_path=document_path,
    )


def relate_chunk_links_to_chunk(
    tx,
    source_chunk_id: str,
    target_chunk_id: str,
    method: str,
    score: float,
    sources: list,
    confidence: float,
    timestamp: str | None = None,
    provenance: dict | None = None,
):
    """Create LINKS_TO relationship between Chunk nodes with semantic linking metadata."""
    tx.run(
        """
        MATCH (sc:Chunk {id: $source_id})
        MATCH (tc:Chunk {id: $target_id})
        MERGE (sc)-[rel:LINKS_TO]->(tc)
        ON CREATE SET rel.method = $method,
                      rel.score = $score,
                      rel.sources = $sources,
                      rel.confidence = $confidence,
                      rel.timestamp = $timestamp,
                      rel.provenance = $provenance
        ON MATCH SET rel.method = coalesce($method, rel.method),
                     rel.score = coalesce($score, rel.score),
                     rel.sources = coalesce($sources, rel.sources),
                     rel.confidence = coalesce($confidence, rel.confidence),
                     rel.timestamp = coalesce($timestamp, rel.timestamp),
                     rel.provenance = coalesce($provenance, rel.provenance)
        """,
        source_id=source_chunk_id,
        target_id=target_chunk_id,
        method=method,
        score=score,
        sources=sources,
        confidence=confidence,
        timestamp=timestamp,
        provenance=provenance,
    )


def relate_requirement_implements_file_enhanced(
    tx,
    requirement_id: str,
    file_path: str,
    sources: list,
    confidence: float,
    commit_hash: str | None = None,
    timestamp: str | None = None,
    provenance: dict | None = None,
):
    """Create enhanced IMPLEMENTS relationship with evidence-based metadata."""
    tx.run(
        """
        MATCH (r:Requirement {id: $req_id})
        MATCH (f:File {path: $file_path})
        MERGE (r)-[rel:IMPLEMENTS]->(f)
        ON CREATE SET rel.sources = $sources,
                      rel.confidence = $confidence,
                      rel.commit = $commit,
                      rel.timestamp = $timestamp,
                      rel.provenance = $provenance
        ON MATCH SET rel.sources = coalesce($sources, rel.sources),
                     rel.confidence = coalesce($confidence, rel.confidence),
                     rel.commit = coalesce($commit, rel.commit),
                     rel.timestamp = coalesce($timestamp, rel.timestamp),
                     rel.provenance = coalesce($provenance, rel.provenance)
        """,
        req_id=requirement_id,
        file_path=file_path,
        sources=sources,
        confidence=confidence,
        commit=commit_hash,
        timestamp=timestamp,
        provenance=provenance,
    )


# -------------------- Phase 0: Directory Hierarchy Helpers --------------------

def merge_directory(tx, directory_info: Dict[str, object]):
    """Merge a Directory node with hierarchy information.
    
    Expected keys: path, depth, parent_path (optional)
    """
    tx.run(
        """
        MERGE (d:Directory {path: $path})
        ON CREATE SET d.depth = $depth,
                      d.uid = $uid,
                      d.parent_path = $parent_path
        ON MATCH SET d.depth = coalesce($depth, d.depth),
                     d.uid = coalesce($uid, d.uid),
                     d.parent_path = coalesce($parent_path, d.parent_path)
        """,
        path=directory_info["path"],
        depth=directory_info.get("depth", 0),
        uid=str(directory_info["path"]) if "path" in directory_info else None,
        parent_path=directory_info.get("parent_path"),
    )


def relate_directory_contains_file(tx, directory_path: str, file_path: str, timestamp: str = None):
    """Create CONTAINS relationship between directory and file."""
    tx.run(
        """
        MATCH (d:Directory {path: $dir_path})
        MERGE (f:File {path: $file_path})
        MERGE (d)-[r:CONTAINS]->(f)
        ON CREATE SET r.timestamp = $timestamp
        ON MATCH SET r.timestamp = coalesce($timestamp, r.timestamp)
        """,
        dir_path=directory_path,
        file_path=file_path,
        timestamp=timestamp,
    )


def relate_directory_contains_directory(tx, parent_path: str, child_path: str, timestamp: str = None):
    """Create CONTAINS relationship between parent and child directories."""
    tx.run(
        """
        MATCH (parent:Directory {path: $parent_path})
        MATCH (child:Directory {path: $child_path})
        MERGE (parent)-[r:CONTAINS]->(child)
        ON CREATE SET r.timestamp = $timestamp
        ON MATCH SET r.timestamp = coalesce($timestamp, r.timestamp)
        """,
        parent_path=parent_path,
        child_path=child_path,
        timestamp=timestamp,
    )


def create_directory_hierarchy(tx, file_paths: List[str], timestamp: str = None):
    """Create complete directory hierarchy from file paths.
    
    This function analyzes file paths and creates all necessary Directory nodes
    and CONTAINS relationships to build a complete hierarchy.
    """
    # Extract all unique directory paths from file paths
    directories = set()
    for file_path in file_paths:
        path_parts = file_path.replace("\\", "/").split("/")
        for i in range(1, len(path_parts)):  # Skip filename, include all parent dirs
            dir_path = "/".join(path_parts[:i])
            if dir_path:  # Skip empty paths
                directories.add(dir_path)
    
    # Create directory nodes with depth information
    for dir_path in sorted(directories):
        depth = dir_path.count("/")
        parent_path = "/".join(dir_path.split("/")[:-1]) if "/" in dir_path else None
        
        merge_directory(tx, {
            "path": dir_path,
            "depth": depth,
            "parent_path": parent_path
        })
    
    # Create CONTAINS relationships for directories
    for dir_path in sorted(directories):
        depth = dir_path.count("/")
        if depth > 0:  # Not root directory
            parent_path = "/".join(dir_path.split("/")[:-1])
            relate_directory_contains_directory(tx, parent_path, dir_path, timestamp)
    
    # Create CONTAINS relationships for files
    for file_path in file_paths:
        dir_path = "/".join(file_path.replace("\\", "/").split("/")[:-1])
        if dir_path:  # File has a parent directory
            relate_directory_contains_file(tx, dir_path, file_path, timestamp)

