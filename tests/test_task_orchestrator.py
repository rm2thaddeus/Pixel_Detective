import time
from components.task_orchestrator import TaskOrchestrator, submit, is_running

def test_submit_and_run():
    results = []
    def work(x):
        time.sleep(0.1)
        results.append(x)

    orchestrator = TaskOrchestrator()
    # First submission should start the task
    assert orchestrator.submit("job1", work, 1) is True
    assert orchestrator.is_running("job1") is True
    # Wait for completion
    time.sleep(0.2)
    assert orchestrator.is_running("job1") is False
    assert results == [1]
    # Submitting again after completion should succeed
    assert orchestrator.submit("job1", work, 2) is True
    time.sleep(0.2)
    assert results == [1, 2]


def test_single_thread_enforcement():
    results = []
    def work():
        time.sleep(0.2)
        results.append("done")
    orchestrator = TaskOrchestrator()
    assert orchestrator.submit("job", work) is True
    # Attempting to submit same name while running should fail
    assert orchestrator.submit("job", work) is False
    time.sleep(0.3)
    assert results == ["done"]
    # After completion, submission should succeed again
    assert orchestrator.submit("job", work) is True


def test_global_submit_functions():
    results = []
    def work_global():
        time.sleep(0.1)
        results.append("global")

    # Use module-level submit/is_running
    assert submit("global", work_global) is True
    assert is_running("global") is True
    time.sleep(0.2)
    assert is_running("global") is False
    assert results == ["global"] 