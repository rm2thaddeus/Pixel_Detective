import os

from developer_graph.sprint_mapping import SprintMapper


def test_map_all_sprints_produces_windows():
    mapper = SprintMapper(os.getcwd())
    result = mapper.map_all_sprints()

    assert isinstance(result, dict)
    assert "count" in result
    assert "windows" in result

    for window in result.get("windows", []):
        assert window.get("start")
        assert window.get("end")
        assert window["start"] <= window["end"]
