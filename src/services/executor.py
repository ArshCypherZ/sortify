import shutil
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Set
from src.config.settings import settings
from src.utils.logger import logger
from src.i18n.strings import Strings

class Executor:
    def __init__(self):
        self.transaction_log_file = settings.DB_FILE.parent / "transactions.json"
        self.transactions: List[Dict] = []
        self._load_transactions()
        
        # Track recently moved files to prevent re-processing (cooldown)
        self._recently_moved: Dict[str, float] = {}  # path -> timestamp
        self._cooldown_seconds = 10.0  # Ignore files for 10 seconds after move

    def _load_transactions(self):
        if self.transaction_log_file.exists():
            try:
                with open(self.transaction_log_file, "r") as f:
                    self.transactions = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load transaction log: {e}")
                self.transactions = []

    def _save_transactions(self):
        try:
            self.transaction_log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.transaction_log_file, "w") as f:
                json.dump(self.transactions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save transaction log: {e}")

    def _get_safe_dest(self, dest: Path) -> Path:
        """
        Returns a unique destination path to avoid overwriting.
        Example: file.txt -> file_v2.txt -> file_v3.txt
        """
        if not dest.exists():
            return dest
        
        stem = dest.stem
        suffix = dest.suffix
        parent = dest.parent
        counter = 2
        
        while True:
            new_dest = parent / f"{stem}_v{counter}{suffix}"
            if not new_dest.exists():
                return new_dest
            counter += 1

    def safe_move(self, src: Path, dest_folder: Path, new_name: Optional[str] = None) -> bool:
        """
        Safely moves a file to the destination folder.
        Handles: Dry Run, Conflict Resolution, Transaction Logging.
        """
        try:
            if not src.exists():
                logger.warning(Strings.FILE_NOT_FOUND.value.format(src))
                return False

            dest_name = new_name if new_name else src.name
            final_dest = self._get_safe_dest(dest_folder / dest_name)
            
            # Dry Run Check
            if settings.DRY_RUN:
                logger.info(f"[DRY RUN] Would move '{src}' to '{final_dest}'")
                return True

            # Create destination folder
            dest_folder.mkdir(parents=True, exist_ok=True)
            
            # Perform Move
            shutil.move(str(src), str(final_dest))
            logger.info(f"Moved '{src.name}' to '{final_dest}'")
            
            # Track this destination to prevent re-processing
            self._recently_moved[str(final_dest.resolve())] = time.time()
            
            # Log Transaction
            self.transactions.append({
                "action": "move",
                "src": str(src), # Original location (now empty)
                "dest": str(final_dest), # New location
                "timestamp": time.time()
            })
            self._save_transactions()
            
            return True

        except Exception as e:
            logger.error(Strings.ERROR_PROCESSING.value.format(src.name, e))
            return False

    def undo_last(self) -> bool:
        """
        Undoes the last action.
        """
        if not self.transactions:
            logger.info("No actions to undo.")
            return False

        last_tx = self.transactions.pop()
        action = last_tx.get("action")
        
        try:
            if action == "move":
                src = Path(last_tx["src"])
                dest = Path(last_tx["dest"])
                
                if dest.exists() and not src.exists():
                    # Move back
                    shutil.move(str(dest), str(src))
                    logger.info(f"Undo: Moved '{dest.name}' back to '{src}'")
                    self._save_transactions()
                    return True
                else:
                    logger.warning(f"Undo failed: File state changed. Dest exists: {dest.exists()}, Src exists: {src.exists()}")
                    return False
            return False
        except Exception as e:
            logger.error(f"Undo failed: {e}")
            return False

    def is_recently_moved(self, file_path: Path) -> bool:
        """
        Check if a file was recently moved by Sortify.
        Used to prevent re-processing files we just placed.
        """
        resolved_path = str(file_path.resolve())
        
        # Cleanup old entries
        current_time = time.time()
        self._recently_moved = {
            p: t for p, t in self._recently_moved.items() 
            if current_time - t < self._cooldown_seconds
        }
        
        if resolved_path in self._recently_moved:
            elapsed = current_time - self._recently_moved[resolved_path]
            if elapsed < self._cooldown_seconds:
                return True
        
        return False

executor = Executor()
