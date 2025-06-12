import threading

class LoadingProgress:
    def __init__(self):
        self.is_loading=False
        self.progress_percentage=0
        self.error_occurred=False
        self.background_prep_started=False
        self.models_loaded=False
        self.database_ready=False

    def update_progress(self, percentage, message):
        self.progress_percentage = percentage
        # The message is not stored in this class, but the method signature
        # should match the test.

class BackgroundLoader:
    def __init__(self):
        self.progress=LoadingProgress()
        self._lock = threading.Lock()

    def get_progress(self):
        with self._lock:
            return self.progress

background_loader = BackgroundLoader()
