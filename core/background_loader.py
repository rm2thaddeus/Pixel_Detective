class LoadingProgress:
    def __init__(self):
        self.is_loading=False
        self.progress_percentage=0
        self.error_occurred=False
        self.background_prep_started=False
        self.models_loaded=False
        self.database_ready=False

class BackgroundLoader:
    def __init__(self):
        self.progress=LoadingProgress()

    def get_progress(self):
        return self.progress

background_loader = BackgroundLoader()
