import threading
from typing import Callable, Any, Dict

class TaskOrchestrator:
    def __init__(self):
        self._threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def _run_and_cleanup(self, name: str, fn: Callable, *args: Any, **kwargs: Any) -> None:
        try:
            fn(*args, **kwargs)
        finally:
            with self._lock:
                self._threads.pop(name, None)

    def submit(self, name: str, fn: Callable, *args: Any, **kwargs: Any) -> bool:
        with self._lock:
            if name in self._threads and self._threads[name].is_alive():
                return False
            thread = threading.Thread(target=self._run_and_cleanup, args=(name, fn, *args), kwargs=kwargs)
            thread.start()
            self._threads[name] = thread
            return True

    def is_running(self, name: str) -> bool:
        with self._lock:
            thread = self._threads.get(name)
            return thread.is_alive() if thread else False

_global_orchestrator = TaskOrchestrator()

def submit(name: str, fn: Callable, *args: Any, **kwargs: Any) -> bool:
    return _global_orchestrator.submit(name, fn, *args, **kwargs)

def is_running(name: str) -> bool:
    return _global_orchestrator.is_running(name)
