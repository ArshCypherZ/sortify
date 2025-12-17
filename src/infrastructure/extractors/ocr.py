import pytesseract
from PIL import Image
from pathlib import Path
from src.utils.logger import logger

class OCRHandler:
    """Layer 2: specialized OCR for Images."""
    def extract_text(self, path: Path) -> str:
        try:
            image = Image.open(path)
            # Simple tesseract call
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.debug(f"OCR failed for {path.name}: {e}")
            return ""
