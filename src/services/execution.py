import shutil
import json
import numpy as np
from pathlib import Path
from datetime import datetime
import uuid
from sqlmodel import Session

from src.services.base import BaseService
from src.services.atlas import atlas
from src.core.events import event_broker
from src.infrastructure.database.engine import get_session
from src.infrastructure.database.models import Transaction, FileIndex
from src.utils.logger import logger
from src.core.classification.classifier import classifier

class ExecutionService(BaseService):
    def _register_handlers(self):
        event_broker.ACTION_PROPOSED.connect(self.handle_action)

    def handle_action(self, sender, path: Path, action: str, destination: Path, file_hash: str, metadata: dict = None, **kwargs):
        if action != "move":
            logger.warning(f"Unsupported action: {action}")
            return

        try:
            self.execute_move(path, destination, file_hash, metadata)
            
            # Feedback Loop: Learning
            if metadata and metadata.get("category") not in ["Unknown", "Unsorted"]:
                keywords = metadata.get("keywords", [])
                if keywords:
                     logger.debug(f"Reinforcing learning for {metadata['category']}")
                     classifier.learn(keywords, metadata['category'])
                
                # Update Atlas cluster with new file embedding
                embedding = metadata.get("embedding")
                if embedding is not None:
                    try:
                        file_embedding = np.array(embedding, dtype=np.float32)
                        atlas.update_cluster(destination.parent, file_embedding)
                    except Exception as e:
                        logger.debug(f"Failed to update Atlas cluster: {e}")
                     
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            event_broker.ACTION_FAILED.send(self, path=path, error=str(e))

    def execute_move(self, src: Path, dest: Path, file_hash: str, metadata: dict = None):
        # 1. Resolve Destination Collision
        final_dest = self._resolve_collision(dest)
        
        # 2. Phase 1: Prepare (Write Intent)
        tx_id = str(uuid.uuid4())
        
        with get_session() as session:
            # Create Transaction Record
            tx = Transaction(
                id=tx_id,
                src_path=str(src),
                dest_path=str(final_dest),
                action_type="move",
                status="pending",
                rollback_data_json=json.dumps({"original_path": str(src)})
            )
            session.add(tx)
            
            # Create/Update FileIndex (mark as pending?)
            # We update FileIndex AFTER success, or here? 
            # Let's insert/update FileIndex at the end.
            
            session.commit()
            
            try:
                # 3. Phase 2: Commit (OS Action)
                final_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(final_dest))
                
                # 4. Finalize DB
                tx.status = "committed"
                session.add(tx)
                
                # Update FileIndex
                # Check if exists
                existing_idx = session.get(FileIndex, file_hash)
                if not existing_idx:
                    existing_idx = FileIndex(file_hash=file_hash, current_path=str(final_dest))
                else:
                    existing_idx.current_path = str(final_dest)
                    existing_idx.last_seen = datetime.now()
                    existing_idx.status = "processed"
                
                session.add(existing_idx)
                session.commit()
                
                logger.info(f"Moved: {src.name} -> {final_dest}")
                event_broker.ACTION_COMPLETED.send(self, path=src, new_path=final_dest)

            except Exception as move_error:
                # Rollback!
                session.refresh(tx)
                tx.status = "failed"
                session.add(tx)
                session.commit()
                raise move_error

    def _resolve_collision(self, dest: Path) -> Path:
        """
        Renames file if destination exists.
        file.pdf -> file_v1.pdf, file_v2.pdf...
        """
        if not dest.exists():
            return dest
            
        counter = 1
        while True:
            new_name = f"{dest.stem}_v{counter}{dest.suffix}"
            new_dest = dest.parent / new_name
            if not new_dest.exists():
                return new_dest
            counter += 1
