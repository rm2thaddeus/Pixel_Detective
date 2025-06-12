import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from utils.duplicate_detector import compute_sha256
from utils.embedding_cache import EmbeddingCache
from models.model_manager import ModelManager
from database.qdrant_connector import QdrantDB
from utils.metadata_extractor import extract_metadata


class IncrementalIndexerHandler(FileSystemEventHandler):
    """
    Watches for file creation, modification, and deletion events and updates Qdrant accordingly.
    """
    def __init__(self, db: QdrantDB, cache: EmbeddingCache, model_mgr: ModelManager, debounce_interval: float = 1.0):
        super().__init__()
        self.db = db
        self.cache = cache
        self.model_mgr = model_mgr
        self.debounce_interval = debounce_interval
        self._last_event_time = {}  # path -> timestamp

    def _should_process(self, path: str) -> bool:
        now = time.time()
        last = self._last_event_time.get(path, 0)
        if now - last < self.debounce_interval:
            return False
        self._last_event_time[path] = now
        return True

    def on_created(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if self._should_process(path):
            self._index_file(path)

    def on_modified(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if self._should_process(path):
            self._index_file(path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        path = event.src_path
        self._delete_file(path)

    def _index_file(self, path: str):
        try:
            # Compute hash
            file_hash = compute_sha256(path)
            embedding = self.cache.get(file_hash)
            if embedding is None:
                embedding = self.model_mgr.process_image(path)
                self.cache.set(file_hash, embedding)
            # Generate caption
            caption = self.model_mgr.generate_caption(path)
            metadata = {'caption': caption}
            # Upsert to Qdrant
            self.db.add_image(path, embedding, metadata)
            print(f"Indexed {path}")
        except Exception as e:
            print(f"Error indexing {path}: {e}")

    def _delete_file(self, path: str):
        try:
            self.db.delete_image(path)
            print(f"Deleted {path} from index")
        except Exception as e:
            print(f"Error deleting {path} from index: {e}")


def start_incremental_indexer(
    folder: str,
    db: QdrantDB,
    cache: EmbeddingCache,
    model_mgr: ModelManager,
    polling_interval: float = 1.0
):
    """
    Launches a watchdog Observer monitoring `folder` recursively.
    Returns the Observer instance so the caller can stop it.
    """
    event_handler = IncrementalIndexerHandler(db, cache, model_mgr, debounce_interval=polling_interval)
    observer = Observer()
    observer.schedule(event_handler, folder, recursive=True)
    observer.start()
    return observer 