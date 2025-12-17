import magic
import mimetypes
from pathlib import Path
from src.utils.logger import logger

class MagicDetector:
    """Layer 1: Surface Telemetry - True Type Detection"""
    def __init__(self):
        try:
            self.magic = magic.Magic(mime=True)
        except Exception as e:
            logger.warning(f"Failed to init python-magic: {e}. Fallback to extensions.")
            self.magic = None

    def detect(self, path: Path) -> str:
        """Returns Mime Type detection using Magic Bytes."""
        if not path.exists():
            return "application/octet-stream"
            
        # 1. Try Magic
        if self.magic:
            try:
                return self.magic.from_file(str(path))
            except Exception as e:
                logger.debug(f"Magic detection failed for {path}: {e}")
                
        # 2. Fallback to mimetypes (extension based)
        mime, _ = mimetypes.guess_type(path)
        return mime or "application/octet-stream"
