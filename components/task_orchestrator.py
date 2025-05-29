import threading
from typing import Callable, Any, Dict


class TaskOrchestrator:
    """Central orchestrator for background tasks."""
    def __init__(self):
        self._lock = threading.Lock()
        self._threads: Dict[str, threading.Thread] = {}

    def submit(self, name: str, fn: Callable[..., Any], *args, **kwargs) -> bool:
        """Submit a task to run in background if not already running."""
        with self._lock:
            thread = self._threads.get(name)
            if thread and thread.is_alive():
                return False
            # Create and start a new daemon thread
            worker = threading.Thread(
                target=self._run_and_cleanup,
                args=(name, fn, args, kwargs),
                daemon=True,
                name=f"TaskOrchestrator-{name}"
            )
            self._threads[name] = worker
            worker.start()
            return True

    def is_running(self, name: str) -> bool:
        """Return True if task with given name is still running."""
        with self._lock:
            thread = self._threads.get(name)
            return bool(thread and thread.is_alive())

    def _run_and_cleanup(self, name: str, fn: Callable[..., Any], args: tuple, kwargs: dict):
        try:
            fn(*args, **kwargs)
        finally:
            with self._lock:
                # Clean up completed thread entry
                thread = self._threads.get(name)
                if thread and not thread.is_alive():
                    del self._threads[name]


# Global orchestrator instance
_orchestrator = TaskOrchestrator()


def submit(name: str, fn: Callable[..., Any], *args, **kwargs) -> bool:
    """Submit task via global orchestrator."""
    return _orchestrator.submit(name, fn, *args, **kwargs)


def is_running(name: str) -> bool:
    """Check task status via global orchestrator."""
    return _orchestrator.is_running(name) 