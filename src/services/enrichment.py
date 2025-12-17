from datetime import datetime
from pathlib import Path
from src.core.models import FileContext
from src.infrastructure.extractors.magic import MagicDetector
from src.infrastructure.extractors.ocr import OCRHandler
from src.infrastructure.extractors.text import Ingestor
from src.utils.logger import logger

class EnrichmentService:
    """
    Service for extracting and enriching file metadata.
    Orchestrates text extraction, MIME type detection, and OCR.
    """
    def __init__(self):
        self.magic = MagicDetector()
        self.ocr = OCRHandler()
        self.ingestor = Ingestor() # Reusing MarkItDown wrapper

    def enrich(self, path: Path) -> FileContext:
        ctx = FileContext(path=path)
        
        # 1. Telemetry
        ctx.mime_type = self.magic.detect(path)
        try:
            stat = path.stat()
            ctx.creation_date = datetime.fromtimestamp(stat.st_ctime) 
        except Exception:
            pass

        # 2. Ingestion (Text)
        # Try MarkItDown first
        text = self.ingestor.extract_text(path)
        
        # 3. Deep OCR Fallback
        # If MarkItDown failed (empty text) AND it's an image, try Tesseract
        if not text and ctx.mime_type.startswith("image/"):
             logger.info(f"MarkItDown extracted no text for image {path.name}. Trying Tesseract OCR...")
             ocr_text = self.ocr.extract_text(path)
             if ocr_text:
                 text = ocr_text
                 logger.info(f"OCR recovered {len(text)} chars from {path.name}")
        
        ctx.text = text
        return ctx

enricher = EnrichmentService()
