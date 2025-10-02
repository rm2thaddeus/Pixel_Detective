from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter

from ..app_state import driver, validator, engine
from ..models import (
    QualityOverviewResponse,
    QualityCategory,
    QualitySection,
    QualityIndicator,
)

try:  # psutil is optional in some environments
    import psutil  # type: ignore
    import os
except Exception:  # pragma: no cover - psutil may not be installed
    psutil = None
    os = None


router = APIRouter()


def _scalar(session, query: str, default: float = 0.0, **params) -> float:
    """Safely execute a scalar Neo4j query and coerce the result to float."""
    try:
        record = session.run(query, params).single()
    except Exception:
        return default
    if not record:
        return default
    if "value" in record:
        return float(record["value"] or 0)
    try:
        first_key = next(iter(record.keys()))
        return float(record[first_key] or 0)
    except Exception:
        return default


def _status_from_threshold(value: float, ok: float, warn: float, higher_is_better: bool = True) -> str:
    """Return status string (ok/warn/critical) based on thresholds."""
    if higher_is_better:
        if value >= ok:
            return "ok"
        if value >= warn:
            return "warn"
        return "critical"
    if value <= ok:
        return "ok"
    if value <= warn:
        return "warn"
    return "critical"


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


@router.get("/api/v1/dev-graph/quality", response_model=QualityOverviewResponse)
def get_quality_overview() -> QualityOverviewResponse:
    """Aggregate data quality, API health, and database health metrics for the dashboard."""
    with driver.session() as session:
        commit_count = _scalar(session, "MATCH (c:GitCommit) RETURN count(c) AS value")
        file_count = _scalar(session, "MATCH (f:File) RETURN count(f) AS value")
        requirement_count = _scalar(session, "MATCH (r:Requirement) RETURN count(r) AS value")
        document_count = _scalar(session, "MATCH (d:Document) RETURN count(d) AS value")
        chunk_count = _scalar(session, "MATCH (ch:Chunk) RETURN count(ch) AS value")
        sprint_count = _scalar(session, "MATCH (s:Sprint) RETURN count(s) AS value")

        total_nodes = commit_count + file_count + requirement_count + document_count + chunk_count + sprint_count

        commits_with_files = _scalar(
            session,
            "MATCH (c:GitCommit)-[:TOUCHED]->(:File) RETURN count(DISTINCT c) AS value",
        )
        files_with_requirements = _scalar(
            session,
            "MATCH (f:File)<-[:IMPLEMENTS]-(:Requirement) RETURN count(DISTINCT f) AS value",
        )
        docs_with_chunks = _scalar(
            session,
            "MATCH (d:Document)-[:CONTAINS_CHUNK]->(:Chunk) RETURN count(DISTINCT d) AS value",
        )
        chunks_linked_to_docs = _scalar(
            session,
            "MATCH (:Document)-[:CONTAINS_CHUNK]->(ch:Chunk) RETURN count(DISTINCT ch) AS value",
        )
        requirements_with_impl = _scalar(
            session,
            "MATCH (r:Requirement)-[:IMPLEMENTS]->(:File) RETURN count(DISTINCT r) AS value",
        )
        avg_files_per_requirement = _scalar(
            session,
            """
            MATCH (r:Requirement)
            OPTIONAL MATCH (r)-[:IMPLEMENTS]->(:File)
            WITH r, count(*) AS file_links
            RETURN coalesce(avg(file_links), 0) AS value
            """,
        )

        touched_edges = _scalar(session, "MATCH (:GitCommit)-[r:TOUCHED]->(:File) RETURN count(r) AS value")
        implements_edges = _scalar(session, "MATCH ()-[r:IMPLEMENTS]->() RETURN count(r) AS value")
        evolves_edges = _scalar(session, "MATCH ()-[r:EVOLVES_FROM]->() RETURN count(r) AS value")
        refactored_edges = _scalar(session, "MATCH ()-[r:REFACTORED_TO]->() RETURN count(r) AS value")
        deprecated_edges = _scalar(session, "MATCH ()-[r:DEPRECATED_BY]->() RETURN count(r) AS value")
        references_edges = _scalar(session, "MATCH ()-[r:REFERENCES]->() RETURN count(r) AS value")
        part_of_edges = _scalar(session, "MATCH ()-[r:PART_OF]->() RETURN count(r) AS value")
        mentions_edges = _scalar(session, "MATCH ()-[r:MENTIONS]->() RETURN count(r) AS value")
        links_to_edges = _scalar(session, "MATCH ()-[r:LINKS_TO]->() RETURN count(r) AS value")

        orphan_nodes = _scalar(session, "MATCH (n) WHERE size((n)--()) = 0 RETURN count(n) AS value")

    schema_checks: Dict[str, bool] = {}
    temporal_issues: Dict[str, int] = {}
    semantic_checks: Dict[str, Any] = {}
    duplicate_relationships: List[Dict[str, Any]] = []

    if validator:
        try:
            schema_checks = validator.validate_schema_completeness()
        except Exception:
            schema_checks = {}
        try:
            temporal_issues = validator.validate_temporal_consistency()
        except Exception:
            temporal_issues = {}
        try:
            semantic_checks = validator.validate_temporal_semantic_graph()
        except Exception:
            semantic_checks = {}
        try:
            duplicate_relationships = validator.detect_duplicate_relationships()
        except Exception:
            duplicate_relationships = []

    chunks_with_embeddings = float(semantic_checks.get("chunks_with_embeddings", 0))
    chunks_without_embeddings = float(semantic_checks.get("chunks_without_embeddings", 0))
    links_with_confidence = float(semantic_checks.get("links_with_confidence", 0))
    links_without_confidence = float(semantic_checks.get("links_without_confidence", 0))

    availability_score = 0.0
    availability_indicators: List[QualityIndicator] = []

    def _add_availability(label: str, count: float, ok: float, warn: float, points: float, description: str) -> None:
        nonlocal availability_score
        status = _status_from_threshold(count, ok, warn)
        availability_score += points if count > 0 else 0
        availability_indicators.append(
            QualityIndicator(
                label=label,
                value=int(count),
                target=int(ok),
                status=status,
                description=description,
            )
        )

    _add_availability("Git commits", commit_count, ok=500, warn=1, points=5, description="Total GitCommit nodes ingested")
    _add_availability("Files", file_count, ok=1200, warn=1, points=4, description="Code/File nodes available")
    _add_availability("Requirements", requirement_count, ok=100, warn=1, points=3, description="Requirement coverage")
    _add_availability("Documents", document_count, ok=40, warn=1, points=3, description="Document knowledge base")
    _add_availability("Chunks", chunk_count, ok=400, warn=1, points=3, description="Semantic chunks extracted")
    _add_availability("Sprints", sprint_count, ok=6, warn=1, points=2, description="Sprint metadata present")

    if commit_count >= 500 and file_count >= 1000:
        availability_score += 2
    if chunk_count > 0 and document_count > 0:
        availability_score += 1
    availability_score = _clamp(availability_score, 0, 20)

    commit_ratio = commits_with_files / commit_count if commit_count else 0.0
    document_ratio = docs_with_chunks / document_count if document_count else 0.0
    chunk_ratio = chunks_linked_to_docs / chunk_count if chunk_count else 0.0
    requirement_ratio = requirements_with_impl / requirement_count if requirement_count else 0.0
    embedding_ratio = chunks_with_embeddings / (chunks_with_embeddings + chunks_without_embeddings) if (chunks_with_embeddings + chunks_without_embeddings) else 0.0

    completeness_indicators: List[QualityIndicator] = [
        QualityIndicator(
            label="Commits with file activity",
            value=round(commit_ratio * 100, 1),
            target=95.0,
            unit="%",
            status=_status_from_threshold(commit_ratio * 100, ok=95, warn=70),
            description="Commits linked to TOUCHED file changes",
        ),
        QualityIndicator(
            label="Documents linked to chunks",
            value=round(document_ratio * 100, 1),
            target=90.0,
            unit="%",
            status=_status_from_threshold(document_ratio * 100, ok=90, warn=65),
            description="Documents that reference extracted chunks",
        ),
        QualityIndicator(
            label="Chunks linked to docs",
            value=round(chunk_ratio * 100, 1),
            target=80.0,
            unit="%",
            status=_status_from_threshold(chunk_ratio * 100, ok=80, warn=55),
            description="Chunks that belong to at least one document",
        ),
        QualityIndicator(
            label="Requirements implemented",
            value=round(requirement_ratio * 100, 1),
            target=75.0,
            unit="%",
            status=_status_from_threshold(requirement_ratio * 100, ok=75, warn=45),
            description="Requirements backed by IMPLEMENTS relationships",
        ),
        QualityIndicator(
            label="Chunks with embeddings",
            value=round(embedding_ratio * 100, 1),
            target=90.0,
            unit="%",
            status=_status_from_threshold(embedding_ratio * 100, ok=90, warn=60),
            description="Vectorized chunks ready for semantic search",
        ),
    ]

    completeness_score = (
        _clamp(commit_ratio * 10, 0, 10)
        + _clamp(document_ratio * 7, 0, 7)
        + _clamp(chunk_ratio * 5, 0, 5)
        + _clamp(requirement_ratio * 3, 0, 3)
    )
    completeness_score = _clamp(completeness_score, 0, 25)

    temporal_total = max(1.0, touched_edges + implements_edges + evolves_edges + refactored_edges + deprecated_edges)
    missing_temporal = float(sum(temporal_issues.values()))
    temporal_missing_ratio = missing_temporal / temporal_total
    temporal_points = (1 - _clamp(temporal_missing_ratio, 0, 1)) * 12

    orphan_ratio = orphan_nodes / total_nodes if total_nodes else 0.0
    orphan_points = (1 - _clamp(orphan_ratio * 5, 0, 1)) * 8

    duplicate_count = float(len(duplicate_relationships))
    duplicate_points = max(0.0, 3 - _clamp(duplicate_count, 0, 3))

    link_total = links_with_confidence + links_without_confidence
    confidence_ratio = links_with_confidence / link_total if link_total else 0.0
    confidence_points = _clamp(confidence_ratio * 2, 0, 2)

    integrity_score = _clamp(temporal_points + orphan_points + duplicate_points + confidence_points, 0, 25)
    integrity_indicators: List[QualityIndicator] = [
        QualityIndicator(
            label="Temporal edges missing timestamp",
            value=int(missing_temporal),
            status=_status_from_threshold(missing_temporal, ok=0.0, warn=5.0, higher_is_better=False),
            description="Temporal relationships without timestamp metadata",
        ),
        QualityIndicator(
            label="Orphan nodes",
            value=int(orphan_nodes),
            status=_status_from_threshold(orphan_nodes, ok=0.0, warn=10.0, higher_is_better=False),
            description="Nodes with no relationships",
        ),
        QualityIndicator(
            label="Duplicate relationship groups",
            value=int(duplicate_count),
            status=_status_from_threshold(duplicate_count, ok=0.0, warn=2.0, higher_is_better=False),
            description="Relationships sharing identical endpoints",
        ),
        QualityIndicator(
            label="Confident LINKS_TO",
            value=round(confidence_ratio * 100, 1),
            target=95.0,
            unit="%",
            status=_status_from_threshold(confidence_ratio * 100, ok=95, warn=70),
            description="LINKS_TO edges populated with confidence metadata",
        ),
    ]

    semantic_edges = (
        implements_edges
        + evolves_edges
        + refactored_edges
        + deprecated_edges
        + references_edges
        + part_of_edges
        + mentions_edges
        + links_to_edges
    )
    semantic_nodes = max(1.0, file_count + chunk_count + requirement_count)
    semantic_density = semantic_edges / semantic_nodes
    semantic_score = _clamp((semantic_density / 4.0) * 20, 0, 20)

    semantic_indicators: List[QualityIndicator] = [
        QualityIndicator(
            label="Semantic relationships",
            value=int(semantic_edges),
            status=_status_from_threshold(semantic_edges, ok=5000, warn=500),
            description="Total IMPLEMENTS/EVOLVES/REF/REFERENCES/PART_OF/MENTIONS/LINKS_TO edges",
        ),
        QualityIndicator(
            label="Median density",
            value=round(semantic_density, 2),
            target=4.0,
            status=_status_from_threshold(semantic_density, ok=4.0, warn=1.5),
            description="Semantic edges per structural node",
        ),
        QualityIndicator(
            label="Enhanced IMPLEMENTS",
            value=int(semantic_checks.get("enhanced_implements", 0)),
            status=_status_from_threshold(semantic_checks.get("enhanced_implements", 0), ok=250, warn=50),
            description="IMPLEMENTS edges enriched with confidence + sources",
        ),
    ]

    coverage_ratio = requirements_with_impl / requirement_count if requirement_count else 0.0
    traceability_score = _clamp(coverage_ratio * 10, 0, 10)
    traceability_indicators: List[QualityIndicator] = [
        QualityIndicator(
            label="Requirement coverage",
            value=round(coverage_ratio * 100, 1),
            target=85.0,
            unit="%",
            status=_status_from_threshold(coverage_ratio * 100, ok=85, warn=55),
            description="Requirements linked to implementing files",
        ),
        QualityIndicator(
            label="Avg files per requirement",
            value=round(avg_files_per_requirement, 2),
            target=1.5,
            status=_status_from_threshold(avg_files_per_requirement, ok=1.5, warn=0.8),
            description="Implementation breadth per requirement",
        ),
    ]

    data_quality_sections = [
        QualitySection(
            key="availability",
            label="Data Availability",
            score=round(availability_score, 2),
            max_score=20,
            summary="Do we have the core entities required for analysis?",
            indicators=availability_indicators,
        ),
        QualitySection(
            key="completeness",
            label="Data Completeness",
            score=round(completeness_score, 2),
            max_score=25,
            summary="How complete are relationships across commits, documents, and requirements?",
            indicators=completeness_indicators,
        ),
        QualitySection(
            key="integrity",
            label="Data Integrity",
            score=round(integrity_score, 2),
            max_score=25,
            summary="Temporal, relationship, and metadata consistency",
            indicators=integrity_indicators,
        ),
        QualitySection(
            key="semantic",
            label="Semantic Richness",
            score=round(semantic_score, 2),
            max_score=20,
            summary="Density of semantic relationships and enriched links",
            indicators=semantic_indicators,
        ),
        QualitySection(
            key="traceability",
            label="Traceability",
            score=round(traceability_score, 2),
            max_score=10,
            summary="Requirements connected to code artifacts",
            indicators=traceability_indicators,
        ),
    ]

    data_quality_score = sum(section.score for section in data_quality_sections)
    data_quality_category = QualityCategory(
        key="data_quality",
        label="Data Quality",
        score=round(data_quality_score, 2),
        max_score=100,
        summary="Holistic quality score across availability, completeness, integrity, richness, and traceability.",
        sections=data_quality_sections,
    )

    engine_metrics: Dict[str, Any] = {}
    if hasattr(engine, "get_metrics"):
        try:
            engine_metrics = engine.get_metrics() or {}
        except Exception:
            engine_metrics = {}

    avg_query_time = float(engine_metrics.get("avg_query_time_ms", 0) or 0)
    cache_hit_rate = float(engine_metrics.get("cache_hit_rate", 0) or 0)
    cache_size = float(engine_metrics.get("cache_size", 0) or 0)
    query_samples = float(engine_metrics.get("query_samples", 0) or 0)
    last_query = engine_metrics.get("last_query_metrics", {}) or {}

    if psutil and os:
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1_000_000.0
        except Exception:
            memory_mb = float(last_query.get("memory_usage_mb", 0) or 0)
    else:
        memory_mb = float(last_query.get("memory_usage_mb", 0) or 0)

    if avg_query_time <= 0:
        responsiveness_score = 28.0
    elif avg_query_time <= 80:
        responsiveness_score = 40.0
    elif avg_query_time <= 140:
        responsiveness_score = 34.0
    elif avg_query_time <= 220:
        responsiveness_score = 28.0
    elif avg_query_time <= 350:
        responsiveness_score = 20.0
    elif avg_query_time <= 500:
        responsiveness_score = 14.0
    else:
        responsiveness_score = 8.0

    responsiveness_indicator = QualityIndicator(
        label="Average query time",
        value=round(avg_query_time, 2),
        unit="ms",
        status=_status_from_threshold(avg_query_time, ok=140, warn=300, higher_is_better=False),
        description="Rolling average latency of engine subgraph queries",
    )

    cache_score = _clamp(cache_hit_rate, 0, 1) * 30
    cache_indicator = QualityIndicator(
        label="Cache hit rate",
        value=round(cache_hit_rate * 100, 1),
        target=80.0,
        unit="%",
        status=_status_from_threshold(cache_hit_rate * 100, ok=75, warn=45),
        description="Portion of requests served from in-memory cache",
    )
    cache_capacity_indicator = QualityIndicator(
        label="Cache size",
        value=int(cache_size),
        status=_status_from_threshold(cache_size, ok=400, warn=50),
        description="Entries currently held in query cache",
    )

    sample_factor = _clamp(query_samples / 180.0, 0, 1)
    sample_score = sample_factor * 18
    memory_score = 12.0 if memory_mb < 1024 else (9.0 if memory_mb < 2048 else 6.0)
    stability_score = _clamp(sample_score + memory_score, 0, 30)

    stability_indicators = [
        QualityIndicator(
            label="Query samples observed",
            value=int(query_samples),
            status=_status_from_threshold(query_samples, ok=180, warn=60),
            description="Count of recent query measurements feeding telemetry",
        ),
        QualityIndicator(
            label="API memory footprint",
            value=round(memory_mb, 1),
            unit="MB",
            status=_status_from_threshold(memory_mb, ok=2048, warn=3072, higher_is_better=False),
            description="Resident memory used by API process",
        ),
    ]

    api_sections = [
        QualitySection(
            key="responsiveness",
            label="Responsiveness",
            score=round(responsiveness_score, 2),
            max_score=40,
            summary="Latency profile for timeline/subgraph queries",
            indicators=[responsiveness_indicator],
        ),
        QualitySection(
            key="caching",
            label="Cache Efficiency",
            score=round(cache_score, 2),
            max_score=30,
            summary="How effectively cached responses avoid recomputation",
            indicators=[cache_indicator, cache_capacity_indicator],
        ),
        QualitySection(
            key="stability",
            label="Operational Stability",
            score=round(stability_score, 2),
            max_score=30,
            summary="Observability signals & resource headroom",
            indicators=stability_indicators,
        ),
    ]

    api_category = QualityCategory(
        key="api_health",
        label="API Health",
        score=round(sum(section.score for section in api_sections), 2),
        max_score=100,
        summary="Latency, caching, and stability signals for the FastAPI layer.",
        sections=api_sections,
    )

    data_volume = commit_count + file_count + chunk_count + requirement_count + document_count
    if data_volume >= 50000:
        volume_score = 35.0
    elif data_volume >= 20000:
        volume_score = 32.0
    elif data_volume >= 5000:
        volume_score = 28.0
    elif data_volume >= 1000:
        volume_score = 24.0
    elif data_volume >= 200:
        volume_score = 18.0
    else:
        volume_score = 12.0

    volume_indicators = [
        QualityIndicator(
            label="Commits",
            value=int(commit_count),
            status=_status_from_threshold(commit_count, ok=5000, warn=500),
            description="Total GitCommit nodes in Neo4j",
        ),
        QualityIndicator(
            label="Files",
            value=int(file_count),
            status=_status_from_threshold(file_count, ok=3000, warn=400),
            description="File nodes available for linking",
        ),
        QualityIndicator(
            label="Chunks",
            value=int(chunk_count),
            status=_status_from_threshold(chunk_count, ok=800, warn=150),
            description="Semantic chunks persisted",
        ),
    ]

    consistency_ratio = (temporal_missing_ratio * 0.5) + (orphan_ratio * 2.0)
    consistency_score = _clamp((1 - _clamp(consistency_ratio, 0, 1)) * 35, 0, 35)

    consistency_indicators = [
        QualityIndicator(
            label="Temporal anomaly ratio",
            value=round(temporal_missing_ratio * 100, 2),
            unit="%",
            status=_status_from_threshold(temporal_missing_ratio * 100, ok=2.5, warn=6, higher_is_better=False),
            description="Share of temporal edges missing timestamps",
        ),
        QualityIndicator(
            label="Orphan ratio",
            value=round(orphan_ratio * 100, 2),
            unit="%",
            status=_status_from_threshold(orphan_ratio * 100, ok=1.0, warn=3.0, higher_is_better=False),
            description="Nodes without relationships",
        ),
    ]

    index_score = 0.0
    index_indicators: List[QualityIndicator] = []
    constraints_available = schema_checks.get("constraints_available", False)
    vector_index = bool(semantic_checks.get("vector_index_available", False) or schema_checks.get("has_vector_index", False))

    if constraints_available:
        index_score += 12
    index_indicators.append(
        QualityIndicator(
            label="Constraints available",
            value=1 if constraints_available else 0,
            status="ok" if constraints_available else "warn",
            description="Neo4j constraints/index metadata accessible",
        )
    )

    if vector_index:
        index_score += 10
    index_indicators.append(
        QualityIndicator(
            label="Vector index",
            value=1 if vector_index else 0,
            status="ok" if vector_index else "warn",
            description="Chunk vector index ready for semantic search",
        )
    )

    core_labels_present = sum(
        1 for key in ["has_gitcommit", "has_file", "has_requirement", "has_document", "has_chunk"] if schema_checks.get(key, False)
    )
    index_score += _clamp(core_labels_present / 5 * 8, 0, 8)

    index_indicators.append(
        QualityIndicator(
            label="Core labels discovered",
            value=core_labels_present,
            target=5,
            status=_status_from_threshold(core_labels_present, ok=5, warn=3),
            description="Presence checks for GitCommit/File/Requirement/Document/Chunk",
        )
    )

    index_score = _clamp(index_score, 0, 30)

    database_sections = [
        QualitySection(
            key="volume",
            label="Data Volume",
            score=round(volume_score, 2),
            max_score=35,
            summary="How much graph data is available for exploration",
            indicators=volume_indicators,
        ),
        QualitySection(
            key="consistency",
            label="Consistency",
            score=round(consistency_score, 2),
            max_score=35,
            summary="Structural health of the stored graph",
            indicators=consistency_indicators,
        ),
        QualitySection(
            key="indexing",
            label="Indexing & Search",
            score=round(index_score, 2),
            max_score=30,
            summary="Query accelerators and label coverage",
            indicators=index_indicators,
        ),
    ]

    database_category = QualityCategory(
        key="database_health",
        label="Database Health",
        score=round(sum(section.score for section in database_sections), 2),
        max_score=100,
        summary="Volume, consistency, and indexing strength for Neo4j storage.",
        sections=database_sections,
    )

    return QualityOverviewResponse(
        categories=[data_quality_category, api_category, database_category],
        generated_at=datetime.utcnow(),
    )
