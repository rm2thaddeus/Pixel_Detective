import os
from unittest.mock import MagicMock

import pytest

from developer_graph.enhanced_git_ingest import EnhancedGitIngester, FileChange
from developer_graph.relationship_deriver import RelationshipDeriver
from developer_graph.routes.analytics import _calculate_quality_score


def _fake_driver_factory(result_map):
    session = MagicMock()
    # Configure successive session.run calls to yield a cursor with .single()
    cursor = MagicMock()
    cursor.single.return_value = result_map
    session.run.return_value = cursor

    context = MagicMock()
    context.__enter__.return_value = session
    context.__exit__.return_value = False

    driver = MagicMock()
    driver.session.return_value = context
    return driver


def test_calculate_quality_score_bounds():
    assert _calculate_quality_score(10, 0, 0) == 100.0
    assert _calculate_quality_score(0, 0, 0) == 0.0
    score = _calculate_quality_score(500, 200, 150)
    assert 0.0 <= score <= 100.0


@pytest.fixture()
def ingester(monkeypatch):
    # Use a fake driver to avoid touching Neo4j during unit tests.
    fake_driver = _fake_driver_factory({
        "missing_commit_uid": 0,
        "missing_is_code": 0,
        "missing_is_doc": 0,
    })
    monkeypatch.setattr(
        "developer_graph.enhanced_git_ingest.GraphDatabase.driver",
        lambda *args, **kwargs: fake_driver,
    )
    mapper = EnhancedGitIngester(os.getcwd(), "bolt://testing", "neo4j", "password")
    mapper.driver = fake_driver  # ensure subsequent calls use the stub
    return mapper


def test_assert_ingest_guards_passes(ingester):
    # Should not raise when all properties are present
    ingester._assert_ingest_guards()


def test_assert_ingest_guards_raises(monkeypatch):
    fake_driver = _fake_driver_factory({
        "missing_commit_uid": 1,
        "missing_is_code": 0,
        "missing_is_doc": 0,
    })
    monkeypatch.setattr(
        "developer_graph.enhanced_git_ingest.GraphDatabase.driver",
        lambda *args, **kwargs: fake_driver,
    )
    mapper = EnhancedGitIngester(os.getcwd(), "bolt://testing", "neo4j", "password")
    mapper.driver = fake_driver

    with pytest.raises(ValueError):
        mapper._assert_ingest_guards()


def test_validate_file_change_flags_invalid(ingester):
    bad_change = FileChange(path="", change_type="X")
    assert ingester._validate_file_change(bad_change) is False


def test_relationship_deriver_derive_all(monkeypatch):
    cursor = MagicMock()
    cursor.__iter__.return_value = []

    session = MagicMock()
    session.run.return_value = cursor

    def execute_write(callback, *args, **kwargs):
        name = getattr(callback, "__name__", "")
        if name == '_derive_implements_relationships':
            return {"count": 2}
        if name == '_derive_evolves_from_relationships':
            return {"count": 1}
        if name == '_derive_depends_on_relationships':
            return {"count": 0}
        if name == '_calculate_confidence_stats':
            return {"avg_confidence": 0.75, "high_confidence": 2, "medium_confidence": 1, "low_confidence": 0}
        if name == '_update_watermarks':
            return None
        return {}

    session.execute_write.side_effect = execute_write

    context = MagicMock()
    context.__enter__.return_value = session
    context.__exit__.return_value = False

    driver = MagicMock()
    driver.session.return_value = context

    deriver = RelationshipDeriver(driver)
    result = deriver.derive_all()

    assert result["implements"] == 2
    assert result["evolves_from"] == 1
    assert result["depends_on"] == 0
    assert result["confidence_stats"]["avg_confidence"] == 0.75
