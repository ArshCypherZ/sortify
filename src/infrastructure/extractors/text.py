from pathlib import Path
from src.config.settings import settings
from src.utils.logger import logger

class Ingestor:
    """
    The 'Eye' of the pipeline.
    Responsibility: Convert files to clean text strings.
    Constraints: 
    - Read only first page (where possible/supported by underlying tools logic)
    - Max character limit to save RAM.
    """
    def __init__(self):
        self._md = None
        self.max_chars = 1200 # Hard limit for RAM optimization

    @property
    def md(self):
        if self._md is None:
            from markitdown import MarkItDown
            self._md = MarkItDown()
        return self._md

    def extract_text(self, file_path: Path) -> str:
        """
        Extracts text from the given file snippet.
        """
        try:
            if not file_path.exists():
                return ""
            
            # Skip expensive/unsupported conversion for binary media
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # List of prefixes/extensions to skip 'markitdown' (which is text-centric)
            # For IMAGES: return empty string so OCR fallback can run in enrichment.py
            # For VIDEO/AUDIO/ARCHIVE: use filename as context (no text extraction possible)
            image_prefixes = ["image/"]
            media_prefixes = ["video/", "audio/", "application/zip", "application/x-tar", "application/x-7z-compressed"]
            skip_exts = {".exe", ".bin", ".iso", ".dll", ".so", ".dylib", ".msi", ".dmg", ".app", ".apk", ".deb", ".rpm"}
            
            # Images: Return empty to trigger OCR in enrichment.py
            if mime_type and any(mime_type.startswith(prefix) for prefix in image_prefixes):
                return ""  # Let OCR handle it
            
            # Other media: Use filename as context
            if (mime_type and any(mime_type.startswith(prefix) for prefix in media_prefixes)) or \
               (file_path.suffix.lower() in skip_exts):
                 # Just use the filename
                 return file_path.stem.replace("_", " ").replace("-", " ")

            # Check size before attempting conversion to avoid hanging on large text files
            if file_path.stat().st_size > 10 * 1024 * 1024: # > 10MB text file is too big for this quick check
                 return file_path.stem.replace("_", " ").replace("-", " ")
            result = self.md.convert(str(file_path))
            text = result.text_content
            
            if not text:
                return ""
            cleaned_text = text[:self.max_chars].strip()
            cleaned_text = " ".join(cleaned_text.split())
            
            return cleaned_text

        except Exception as e:
            logger.debug(f"Ingestion skipped/failed for {file_path.name}: {e}")
            return file_path.stem.replace("_", " ").replace("-", " ")
