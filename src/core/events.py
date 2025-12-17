import logging
from blinker import signal

logger = logging.getLogger("sortify.events")

class EventBroker:
    """
    Central Event Bus using Blinker.
    Decouples components by allowing them to publish/subscribe to named events.
    """
    
    # Event Definitions
    FILE_CREATED = signal("file-created")          # Payload: {path: Path}
    FILE_HASHED = signal("file-hashed")            # Payload: {path: Path, hash: str}
    FILE_READY = signal("file-ready")              # Payload: {path: Path, hash: str}
    
    ANALYSIS_STARTED = signal("analysis-started")  # Payload: {path: Path}
    FILE_CLASSIFIED = signal("file-classified")    # Payload: {path: Path, category: str, confidence: float, metadata: dict}
    
    ACTION_PROPOSED = signal("action-proposed")    # Payload: {path: Path, action: str, destination: Path}
    ACTION_COMPLETED = signal("action-completed")  # Payload: {path: Path, new_path: Path}
    ACTION_FAILED = signal("action-failed")        # Payload: {path: Path, error: str}
    
    ERROR = signal("system-error")                 # Payload: {source: str, error: Exception}
    
    def __init__(self):
        self._setup_logging()

    def _setup_logging(self):
        self.FILE_CREATED.connect(self._log_event)
        self.ACTION_COMPLETED.connect(self._log_event)
        self.ERROR.connect(self._log_error)

    def _log_event(self, sender, **kwargs):
        sender_name = getattr(sender, 'name', str(sender))
        logger.debug(f"Event {sender_name} fired with args: {kwargs}")

    def _log_error(self, sender, **kwargs):
        logger.error(f"Error Event from {sender}: {kwargs.get('error')}")

event_broker = EventBroker()
