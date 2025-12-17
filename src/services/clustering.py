from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import deque
from src.utils.logger import logger

@dataclass
class FileEvent:
    path: str
    category: str
    timestamp: datetime = field(default_factory=datetime.now)

class SessionManager:
    """
    Maintains a 'Short-term Memory' of recent file operations.
    Goal: Identify 'Sessions' (e.g. User downloading 5 Physics papers in 3 mins).
    """
    def __init__(self, window_minutes: int = 5):
        self.window = timedelta(minutes=window_minutes)
        # We store events chronologically
        self.history: deque[FileEvent] = deque(maxlen=50) 
        
    def add_event(self, path: str, category: str):
        if category == "Unknown":
            return
        event = FileEvent(path, category)
        self.history.append(event)
        
    def get_current_session_context(self) -> Dict[str, float]:
        """
        Returns a distribution of categories from the last 'window' minutes.
        e.g. {"Documents": 0.8, "Images": 0.2}
        """
        now = datetime.now()
        recent_events = [
            e for e in self.history 
            if now - e.timestamp < self.window
        ]
        
        if not recent_events:
            return {}
            
        counts = {}
        for e in recent_events:
            counts[e.category] = counts.get(e.category, 0) + 1
            
        total = len(recent_events)
        distribution = {cat: count / total for cat, count in counts.items()}
        dominant = max(distribution, key=distribution.get)
        logger.debug(f"Session Context: {len(recent_events)} files recently. Dominant: {dominant} ({distribution[dominant]:.2f})")
        
        return distribution

session_manager = SessionManager()
