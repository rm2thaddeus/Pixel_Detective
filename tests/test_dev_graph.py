from developer_graph.ingest import DevGraphIngester
from pathlib import Path

def test_extract_requirements():
    prd = Path('docs/sprints/sprint-10/PRD.md')
    ingester = DevGraphIngester('.', 'bolt://localhost:7687', 'neo4j', 'test')
    reqs = ingester.extract_requirements(str(prd))
    assert any(r['id'] == 'FR-10-01' for r in reqs)


def test_parse_libraries():
    ingester = DevGraphIngester('.', 'bolt://localhost:7687', 'neo4j', 'test')
    libs = ingester.parse_libraries()
    assert 'fastapi' in libs
