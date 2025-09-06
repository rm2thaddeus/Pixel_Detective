"""Pydantic models for API response validation."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


class NodeModel(BaseModel):
    """Model for graph nodes."""
    id: str
    labels: Optional[List[str]] = None
    type: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    size: Optional[float] = None


class EdgeModel(BaseModel):
    """Model for graph edges."""
    from_: str = Field(alias="from")
    to: str
    type: str
    timestamp: Optional[str] = None
    rid: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class PaginationModel(BaseModel):
    """Model for pagination information."""
    total_nodes: Optional[int] = None
    total_edges: Optional[int] = None
    returned_nodes: int
    returned_edges: int
    limit: int
    cursor: Optional[str] = None
    next_cursor: Optional[str] = None
    has_more: bool


class PerformanceModel(BaseModel):
    """Model for performance metrics."""
    query_time_ms: float
    cache_hit: bool
    filters: Optional[Dict[str, Any]] = None


class WindowedSubgraphResponse(BaseModel):
    """Model for windowed subgraph API response."""
    nodes: List[NodeModel]
    edges: List[EdgeModel]
    pagination: PaginationModel
    performance: PerformanceModel


class BucketModel(BaseModel):
    """Model for commit buckets."""
    bucket: str
    commit_count: int
    file_changes: int
    granularity: str


class CommitsBucketsResponse(BaseModel):
    """Model for commits buckets API response."""
    buckets: List[BucketModel]
    performance: Dict[str, Any]


class ActivityMetrics(BaseModel):
    """Model for activity metrics."""
    commits_per_day: float
    files_changed_per_day: float
    authors_per_day: float
    peak_activity: Dict[str, Any]
    trends: List[Dict[str, Any]]


class GraphMetrics(BaseModel):
    """Model for graph metrics."""
    total_nodes: int
    total_edges: int
    node_types: Dict[str, int]
    edge_types: Dict[str, int]
    complexity_metrics: Dict[str, float]


class TraceabilityMetrics(BaseModel):
    """Model for traceability metrics."""
    implemented_requirements: int
    unimplemented_requirements: int
    avg_files_per_requirement: float
    coverage_percentage: float


class AnalyticsResponse(BaseModel):
    """Model for combined analytics API response."""
    activity: ActivityMetrics
    graph: GraphMetrics
    traceability: TraceabilityMetrics


class HealthResponse(BaseModel):
    """Model for health check response."""
    status: str
    service: str
    version: str
    database: str
    timestamp: str
    avg_query_time_ms: Optional[float] = None
    cache_hit_rate: Optional[float] = None
    memory_usage_mb: Optional[float] = None


class StatsResponse(BaseModel):
    """Model for stats API response."""
    summary: Dict[str, int]
    node_types: List[Dict[str, Any]]
    relationship_types: List[Dict[str, Any]]
    timestamp: str
