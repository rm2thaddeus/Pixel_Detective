from developer_graph.git_history_service import GitHistoryService
import os


def test_get_commits_returns_list():
    repo_path = os.getcwd()
    svc = GitHistoryService(repo_path)
    commits = svc.get_commits(limit=5)
    assert isinstance(commits, list)
    if commits:
        c = commits[0]
        assert 'hash' in c and 'timestamp' in c and 'message' in c


def test_file_history_handles_missing_file():
    repo_path = os.getcwd()
    svc = GitHistoryService(repo_path)
    events = svc.get_file_history('path/that/does/not/exist.txt', limit=5)
    # Should not raise; may return empty or entries if file existed historically
    assert isinstance(events, list)


