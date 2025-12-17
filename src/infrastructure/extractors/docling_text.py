from pathlib import Path
from pathlib import Path
from src.utils.logger import logger

class TextExtractor:
    def __init__(self):
        self._md = None
        self._doc_converter = None

    @property
    def md(self):
        if self._md is None:
            from markitdown import MarkItDown
            self._md = MarkItDown()
        return self._md

    @property
    def doc_converter(self):
        if self._doc_converter is None:
            from docling.document_converter import DocumentConverter
            self._doc_converter = DocumentConverter()
        return self._doc_converter

    def extract(self, file_path: Path, max_chars: int = 2000) -> str:
        """
        Extracts text from a file using MarkItDown or Docling.
        Returns the first `max_chars` characters to save processing time.
        """
        try:
            # MarkItDown supports many formats (PDF, Docx, Images via OCR if configured)
            # It's a good general purpose tool.
            result = self.md.convert(str(file_path))
            text = result.text_content
            
            if not text.strip():
                # Fallback to Docling for complex PDFs if MarkItDown fails or returns empty
                # Docling is very strong for PDFs
                if file_path.suffix.lower() == ".pdf":
                    logger.info(f"MarkItDown returned empty text, trying Docling for {file_path.name}")
                    conv_result = self.doc_converter.convert(file_path)
                    text = conv_result.document.export_to_markdown()

            return text[:max_chars]
            
        except Exception as e:
            logger.error(f"Extraction failed for {file_path.name}: {e}")
            return ""

extractor = TextExtractor()
