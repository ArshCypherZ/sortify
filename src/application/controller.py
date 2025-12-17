import queue
from src.infrastructure.filesystem.watcher import FileWatcher
from src.core.events import event_broker
from src.services import start_all_services
from src.infrastructure.database.engine import init_db
from src.application.processor import EventProcessor

class SortifyController:
    def __init__(self):
        self.watcher = FileWatcher()
        self.services = []
        self.ui = None
        self.processing_queue = queue.Queue()
        self.processor = EventProcessor(self.processing_queue)

    def start(self, progress_callback=None):
        import threading
        init_db()
        event_broker.FILE_CREATED.connect(self._on_file_created)
        event_broker.FILE_CLASSIFIED.connect(self._notify_ui_classification)
        event_broker.ACTION_COMPLETED.connect(self._notify_ui_action)
        event_broker.ERROR.connect(self._notify_ui_error)

        def _startup_sequence():
            try:
                if self.ui:
                    self.ui.notify("Startup", "Initializing AI Engine...")

                from src.services.atlas import atlas
                if progress_callback:
                    atlas.set_progress_callback(progress_callback)
                atlas.initialize()
                
                if self.ui:
                    self.ui.notify("Startup", "Scanning folder context...")
                    
                from src.infrastructure.filesystem.scanner import scanner
                from src.config.settings import settings
                from src.core.classification.classifier import classifier
                
                discovered_map = scanner.scan()
                
                for cat, path in discovered_map.items():
                    if cat not in settings.CATEGORY_MAP:
                        settings.CATEGORY_MAP[cat] = path
                        
                classifier.update_dynamic_categories(discovered_map)
                        
                self.services = start_all_services()
                self.processor.start()
                self.watcher.start()
                if self.ui:
                    self.ui.notify("Startup", "Ready! Sortify is active.")
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                if self.ui:
                    self.ui.notify("Error", f"Startup Failed: {e}")

        thread = threading.Thread(target=_startup_sequence, daemon=True)
        thread.start()

    def stop(self):
        self.watcher.stop()
        self.processor.stop()
        
    def pause(self):
        self.watcher.pause()
        self.processor.pause()
        
    def resume(self):
        self.watcher.resume()
        self.processor.resume()

    def _on_file_created(self, sender, path=None, **kwargs):
        if path:
            self.processing_queue.put(path)
        if self.ui:
            self.ui.notify("File Detected", f"{path.name}")

    def _notify_ui_classification(self, sender, path=None, category=None, **kwargs):
        if self.ui:
            self.ui.notify("Classified", f"{path.name} -> {category}")

    def _notify_ui_action(self, sender, path=None, new_path=None, **kwargs):
        if self.ui:
            self.ui.notify("Moved", f"{path.name} -> {new_path}")

    def _notify_ui_error(self, sender, error=None, **kwargs):
        if self.ui:
            self.ui.notify("Error", str(error))
