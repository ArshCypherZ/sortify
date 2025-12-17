
import threading
from pathlib import Path
from watchfiles import watch, Change
from src.config.settings import settings
from src.utils.logger import logger

from src.core.events import event_broker

class FileWatcher:
    def __init__(self):
        self.stop_event = threading.Event()
        self.watch_thread = None
        self.paused = False

    def pause(self):
        self.paused = True
        logger.info("Watcher paused.")

    def resume(self):
        self.paused = False
        logger.info("Watcher resumed.")

    def start(self):
        """Starts the file watcher in a separate thread."""
        if self.watch_thread and self.watch_thread.is_alive():
            logger.warning("Watcher already running.")
            return

        self.stop_event.clear()
        self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.watch_thread.start()
        logger.info(f"Watcher started on: {[str(p) for p in settings.WATCH_DIRECTORIES]}")

    def stop(self):
        """Stops the file watcher."""
        if self.watch_thread:
            self.stop_event.set()
            self.watch_thread.join(timeout=1.0)
            logger.info("Watcher stopped.")

    def _watch_loop(self):
        """Internal loop to watch directories."""
        try:
            for changes in watch(*settings.WATCH_DIRECTORIES, stop_event=self.stop_event, recursive=False):
                for change_type, path_str in changes:
                    if change_type == Change.added:
                        if self.paused:
                            continue
                        path = Path(path_str)
                        if self._should_process(path):
                            logger.info(f"New file detected: {path.name}")
                            # Publish Event
                            event_broker.FILE_CREATED.send(self, path=path)
        except Exception as e:
            logger.error(f"Watcher error: {e}")

    def _should_process(self, path: Path) -> bool:
        """
        Check if file should be processed based on ignore patterns.
        """
        if path.is_dir():
            return False
            
        # Check ignore patterns
        for pattern in settings.IGNORE_PATTERNS:
            if path.match(pattern):
                return False

        # Ignore incomplete downloads and temp files
        if path.suffix in {".crdownload", ".part", ".tmp", ".download", ".aria2"}:
            return False
                
        # Check if file is hidden (starts with .)
        if path.name.startswith("."):
            return False
            
        return True
