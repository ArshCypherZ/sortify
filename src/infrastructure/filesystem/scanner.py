import os
from pathlib import Path
from typing import Dict, List
from src.config.settings import settings
from src.core.classification.classifier import classifier
from src.utils.logger import logger

class ContextScanner:
    """
    The 'Scout'. Scans user directories to find existing folders that semantically match our categories.
    """
    def __init__(self):
        # "Scan whole disk" - well, let's scan the Home Directory
        self.roots = settings.SCAN_ROOTS + [Path.home()]
        # Remove duplicates
        self.roots = list(set(self.roots))
        
        # Increase depth to find nested project folders
        self.max_depth = 4
        self.ignore_names = {
            ".git", "__pycache__", "node_modules", "venv", ".sortify", 
            "downloads", "public", "templates", "chroma_db", "data", "db", 
            "build", "dist", "target", "bin", "obj", "lib", "include",
            "assets", "static", "private", "utils",
            "components", "pages", "hooks", "styles", "logs", "tmp", "temp",
            "debug", "release", "x64", "x86", "config", "settings", "env"
        }
        # Ensure all are lowercase for case-insensitive camparisons
        self.ignore_names = {n.lower() for n in self.ignore_names}
        import re
        self.uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

    def scan(self) -> Dict[str, Path]:
        """
        Scans roots and returns a map of {Category: Path}.
        """
        logger.info("Scanning for context-aware folders...")
        discovered = {}
        
        for root in self.roots:
            if not root.exists():
                continue
                
            try:
                # Walk with depth limit
                root_path = str(root)
                root_depth = root_path.count(os.sep)
                
                for current, dirs, files in os.walk(root_path):
                    current_path = Path(current)
                    
                    # Check depth
                    if current_path.name.lower() in self.ignore_names or current_path.name.startswith("."):
                         dirs[:] = []
                         continue
                    
                    # Ignore UUIDs / Hashes
                    if self.uuid_pattern.match(current_path.name):
                         dirs[:] = []
                         continue

                    depth = current.count(os.sep) - root_depth
                    if depth > self.max_depth:
                        dirs[:] = []
                        continue
                        
                    # Evaluate current folder name
                    # Don't evaluate the root itself usually, unless it's like "My Finance"
                    if depth > 0:
                        self._evaluate_folder(current_path, discovered)
                        
            except Exception as e:
                logger.warning(f"Failed to scan {root}: {e}")
                
        logger.info(f"Context Discovery: Found {len(discovered)} mapped folders.")
        return discovered

    def _evaluate_folder(self, path: Path, discovered: Dict[str, Path]):
        folder_name = path.name        
        category_key = folder_name
        
        if category_key not in discovered:
            logger.debug(f"Discovered dynamic category: '{category_key}' -> {path}")
            discovered[category_key] = path

scanner = ContextScanner()
