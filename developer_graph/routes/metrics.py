from __future__ import annotations

from fastapi import APIRouter
from ..app_state import engine
from .unified_ingest import ingestion_state, ingestion_jobs
from typing import Optional, Dict, Any
import time


TARGET_CHUNKS_PER_MIN = 600

router = APIRouter()


def _latest_job() -> Optional[Dict[str, Any]]:
    if not ingestion_jobs:
        return None
    return max(ingestion_jobs.values(), key=lambda job: job.get('finished_at') or job.get('updated_at') or 0)


@router.get("/api/v1/dev-graph/metrics")
def get_metrics():
    metrics = engine.get_metrics() if hasattr(engine, "get_metrics") else {}
    mem_mb = 0.0
    try:
        import psutil, os as _os
        mem_mb = psutil.Process(_os.getpid()).memory_info().rss / 1_000_000.0
    except Exception:
        mem_mb = 0.0

    job = _latest_job()
    stage_metrics = {}
    alerts = []
    slow_documents = []
    slow_code = []
    if job:
        progress = job.get('progress', {})
        stage2 = progress.get('stage_2') or {}
        stage3 = progress.get('stage_3') or {}
        stage6 = progress.get('stage_6') or {}

        if stage2.get('duration'):
            commits_per_sec = stage2.get('commits_ingested', 0) / stage2['duration'] if stage2['duration'] > 0 else 0.0
            stage_metrics['stage_2'] = {
                'commits_ingested': stage2.get('commits_ingested', 0),
                'duration': stage2['duration'],
                'commits_per_second': round(commits_per_sec, 3),
            }
        if stage3.get('duration'):
            chunks_per_sec = stage3.get('total_chunks', 0) / stage3['duration'] if stage3['duration'] > 0 else 0.0
            chunks_per_min = chunks_per_sec * 60.0
            target = TARGET_CHUNKS_PER_MIN * (stage3.get('max_workers', 1) / 8.0 if stage3.get('max_workers') else 1.0)
            below_target = chunks_per_min < target
            stage_metrics['stage_3'] = {
                'total_chunks': stage3.get('total_chunks', 0),
                'duration': stage3['duration'],
                'chunks_per_second': round(chunks_per_sec, 3),
                'chunks_per_minute': round(chunks_per_min, 2),
                'target_chunks_per_minute': round(target, 2),
                'below_target': below_target,
            }
            if below_target:
                alerts.append('stage_3_throughput_below_target')
            slow_documents = stage3.get('slow_documents', [])
            slow_code = stage3.get('slow_code', [])
        if stage6:
            stage_metrics['stage_6'] = {
                'implements': stage6.get('implements', 0),
                'evolves_from': stage6.get('evolves_from', 0),
                'depends_on': stage6.get('depends_on', 0),
                'depends_on_skipped': stage6.get('depends_on_skipped', False),
            }

    metric_payload = {**metrics, "memory_usage_mb": round(mem_mb, 2)}
    metric_payload['ingestion'] = {
        'job_id': ingestion_state.get('ingestion_job_id'),
        'is_running': ingestion_state.get('is_running'),
        'current_stage': ingestion_state.get('current_stage'),
        'job': job,
        'stage_metrics': stage_metrics,
        'alerts': alerts,
        'slow_documents': slow_documents,
        'slow_code': slow_code,
    }
    return metric_payload

