from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from src.core.models import FileContext
from .classifier import classifier
from src.services.memory import memory
from src.infrastructure.llm.nli import FallbackHandler
from src.config.settings import settings
from src.utils.logger import logger
from src.infrastructure.embeddings.sentence_transformer import model_manager

from src.services.clustering import session_manager

class Voter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
        
    @property
    @abstractmethod
    def weight(self) -> float:
        pass

    @abstractmethod
    def vote(self, context: FileContext) -> Tuple[str, float]:
        """Returns (Category, Confidence 0-1)"""
        pass

class SessionVoter(Voter):
    name = "Session"
    weight = 0.5
    
    def vote(self, context: FileContext) -> Tuple[str, float]:
        context_dist = session_manager.get_current_session_context()
        if not context_dist:
            return "Unknown", 0.0
            
        best_cat = max(context_dist, key=context_dist.get)
        confidence = context_dist[best_cat]
        if confidence > 0.5:
             return best_cat, min(confidence, 0.9)
             
        return "Unknown", 0.0

class FileTypeVoter(Voter):
    """Voter A: The "Fast Pass" - MIME/Extension based."""
    name = "FileType"
    weight = 0.3
    
    def vote(self, context: FileContext) -> Tuple[str, float]:
        mime = context.mime_type
        if mime.startswith('image/'): return "Images", 0.9
        if mime.startswith('video/'): return "Video", 0.9
        if mime.startswith('audio/'): return "Audio", 0.9
        if mime.startswith('text/x-python') or context.extension == '.py': return "Code", 0.8
        if mime == 'application/pdf': return "Documents", 0.5
        
        cat = classifier.classify_by_extension(context.path)
        if cat != "Unknown":
            return cat, 0.6
            
        return "Unknown", 0.0

class SemanticVoter(Voter):
    """Semantic classification using keyword embeddings."""
    name = "Semantic"
    weight = 0.6
    
    def vote(self, context: FileContext) -> Tuple[str, float]:
        if not context.text:
            return "Unknown", 0.0

        import re
        keywords = re.findall(r'\w+', context.text.lower())[:50]
        cat, score = classifier.classify_by_keywords(keywords)
        
        if cat != "Unknown":
            return cat, score
             
        return "Unknown", 0.0

class HistoryVoter(Voter):
    """Classification based on previously learned examples."""
    name = "History"
    weight = 0.8
    
    def vote(self, context: FileContext) -> Tuple[str, float]:
        if not context.text:
            return "Unknown", 0.0
        
        try:
            model = model_manager.get_embedding_model()
            embedding = model.encode(context.text[:500])
            category, score = memory.recall(embedding, threshold=0.70)
            
            if category:
                logger.debug(f"HistoryVoter: Recalled '{category}' (score: {score:.2f})")
                return category, score
                
        except Exception as e:
            logger.debug(f"HistoryVoter failed: {e}")
            
        return "Unknown", 0.0

class NLIVoter(Voter):
    """NLI-based zero-shot classification."""
    name = "NLI"
    weight = 0.9
    
    def __init__(self):
        self.handler = FallbackHandler()
        
    def vote(self, context: FileContext) -> Tuple[str, float]:
        if not context.text: return "Unknown", 0.0
        
        candidates = list(settings.CATEGORY_MAP.keys())
        cat = self.handler.reason_placement(str(context.path), context.text, candidates)
        
        if cat != "Unknown":
            return cat, 0.85
            
        return "Unknown", 0.0
