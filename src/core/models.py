from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
import numpy as np

@dataclass
class FileContext:
    path: Path
    mime_type: str = "application/octet-stream"
    creation_date: datetime = field(default_factory=datetime.now)
    text: str = ""
    metadata: Dict = field(default_factory=dict)
    
    @property
    def extension(self) -> str:
        return self.path.suffix.lower()

MIN_FILES_FOR_CENTROID = 3

class FolderCluster:
    """Represents a folder as a cluster with a centroid embedding."""
    
    def __init__(self, path: str, centroid: np.ndarray = None, 
                 name_embedding: np.ndarray = None, n_files: int = 0):
        self.path = path
        self.centroid = centroid  # Average embedding of file contents
        self.name_embedding = name_embedding 
        self.n_files = n_files
    
    def update_centroid(self, new_embedding: np.ndarray):
        """Incrementally update centroid using running average."""
        if self.centroid is None:
            self.centroid = new_embedding
            self.n_files = 1
        else:
            # Running average formula: new_avg = old_avg + (new_val - old_avg) / (n + 1)
            self.n_files += 1
            self.centroid = self.centroid + (new_embedding - self.centroid) / self.n_files
    
    def get_effective_embedding(self) -> Optional[np.ndarray]:
        """Returns centroid if available, else name embedding."""
        if self.centroid is not None and self.n_files >= MIN_FILES_FOR_CENTROID:
            return self.centroid
        return self.name_embedding
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "centroid": self.centroid.tolist() if self.centroid is not None else None,
            "name_embedding": self.name_embedding.tolist() if self.name_embedding is not None else None,
            "n_files": self.n_files
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FolderCluster":
        return cls(
            path=data["path"],
            centroid=np.array(data["centroid"], dtype=np.float32) if data.get("centroid") else None,
            name_embedding=np.array(data["name_embedding"], dtype=np.float32) if data.get("name_embedding") else None,
            n_files=data.get("n_files", 0)
        )
