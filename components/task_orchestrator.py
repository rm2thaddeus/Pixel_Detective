import threading
from typing import Callable, Any, Dict

class TaskOrchestrator:
    """Simple thread-based orchestrator to run named tasks sequentially."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: Dict[str, threading.Thread] = {}

    def submit(self, name: str, func: Callable[..., Any], *args: Any) -> bool:
        """Submit a task if not already running."""
        with self._lock:
            if name in self._tasks and self._tasks[name].is_alive():
                return False
            thread = threading.Thread(target=self._run, args=(name, func, args))
            thread.start()
            self._tasks[name] = thread
            return True

    def _run(self, name: str, func: Callable[..., Any], args: tuple) -> None:
        try:
            func(*args)
        finally:
            with self._lock:
                self._tasks.pop(name, None)

    def is_running(self, name: str) -> bool:
        with self._lock:
            t = self._tasks.get(name)
            return t.is_alive() if t else False


_global_orchestrator = TaskOrchestrator()


def submit(name: str, func: Callable[..., Any], *args: Any) -> bool:
    return _global_orchestrator.submit(name, func, *args)


def is_running(name: str) -> bool:
    return _global_orchestrator.is_running(name)

