from src.utils.logger import logger
from src.core.events import event_broker

class BaseService:
    def __init__(self):
        self.name = self.__class__.__name__
    
    def start(self):
        logger.info(f"Starting Service: {self.name}")
        self._register_handlers()
        
    def _register_handlers(self):
        pass
