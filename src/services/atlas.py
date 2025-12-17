"""
Atlas Service - Cluster-Based File Organization

Treats folders as clusters with computed centroids based on file contents.
Incoming files are matched to folders by comparing their embedding to folder centroids.
"""
import os
import time
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

from src.config.settings import settings
from src.utils.logger import logger
from src.infrastructure.embeddings.sentence_transformer import model_manager
from src.services.enrichment import enricher
from src.core.models import FolderCluster, MIN_FILES_FOR_CENTROID

# Supported file extensions for content embedding
SUPPORTED_EXTENSIONS = {
    '.txt', '.md', '.pdf', '.docx', '.doc', '.pptx', '.ppt',
    '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs',
    '.json', '.yaml', '.yml', '.xml', '.html', '.css',
    '.csv', '.xlsx', '.xls'
}

class AtlasService:
    """
    The Atlas: Cluster-Based Folder Matching.
    
    Each folder is represented as a cluster with:
    - A centroid computed from file contents (if >= N files)
    - A fallback embedding from folder name
    
    Incoming files are matched to the folder whose centroid is most similar.
    """
    
    def __init__(self):
        self.index_file = Path.home() / ".sortify" / "atlas_v2.json"
        self.clusters: Dict[str, FolderCluster] = {}
        
        # Computed embedding matrix for fast search
        self._embedding_matrix: Optional[np.ndarray] = None
        self._path_index: List[str] = []
        
        # Config
        self.scan_roots = [
            Path.home() / "Desktop", 
            Path.home() / "Documents", 
            Path.home() / "Downloads"
        ]
        self.max_depth = 4
        self.ignore_folders = {
            ".git", "node_modules", "venv", "__pycache__", ".sortify", 
            "build", "dist", "tmp", "temp", "logs", "cache", ".cache",
            ".local", ".config", "env", ".env"
        }
        
        # Progress callback for UI
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """Set callback for progress updates: callback(current, total, message)"""
        self._progress_callback = callback

    def _report_progress(self, current: int, total: int, message: str):
        """Report progress to UI if callback is set."""
        if self._progress_callback:
            self._progress_callback(current, total, message)
        if current % 10 == 0 or current == total:
            logger.info(f"Atlas: {message} ({current}/{total})")

    def initialize(self):
        """Load existing index or perform initial scan."""
        if self.index_file.exists():
            self.load()
        else:
            self.scan()

    def scan(self, force_rescan: bool = False):
        """
        Performs a scan to build folder clusters.
        
        Phase 1: Discover all folders
        Phase 2: Compute embeddings for folder names
        Phase 3: Sample files from each folder to compute content centroids
        """
        logger.info("Atlas: Starting cluster-based filesystem scan...")
        start_time = time.time()
        
        # Phase 1: Discover folders
        discovered_folders = self._discover_folders()
        total_folders = len(discovered_folders)
        logger.info(f"Atlas: Discovered {total_folders} folders")
        
        if total_folders == 0:
            logger.warning("Atlas: No folders found to index.")
            return
        
        model = model_manager.get_embedding_model()
        
        # Phase 2: Compute folder name embeddings (fast batch operation)
        self._report_progress(0, total_folders, "Computing folder name embeddings...")
        folder_names = [Path(p).name for p in discovered_folders]
        name_embeddings = model.encode(folder_names, show_progress_bar=False)
        
        # Initialize clusters with name embeddings
        for i, folder_path in enumerate(discovered_folders):
            self.clusters[folder_path] = FolderCluster(
                path=folder_path,
                name_embedding=name_embeddings[i]
            )
        
        # Phase 3: Compute content centroids by sampling files
        self._report_progress(0, total_folders, "Computing folder content centroids...")
        
        for idx, folder_path in enumerate(discovered_folders):
            self._report_progress(idx + 1, total_folders, f"Scanning {Path(folder_path).name}")
            self._compute_folder_centroid(folder_path, model)
        
        # Build search index
        self._rebuild_search_index()
        self.save()
        
        elapsed = time.time() - start_time
        logger.info(f"Atlas: Scan complete in {elapsed:.2f}s. Indexed {len(self.clusters)} folders.")

    def _discover_folders(self) -> List[str]:
        """Walk filesystem to discover indexable folders."""
        discovered = []
        scan_root_names = {root.name.lower() for root in self.scan_roots}
        
        for root in self.scan_roots:
            if not root.exists():
                continue
            
            root_depth = str(root).count(os.sep)
            
            for current, dirs, files in os.walk(root):
                current_path = Path(current).resolve()
                depth = str(current).count(os.sep) - root_depth
                
                # Pruning
                if depth > self.max_depth:
                    dirs[:] = []
                    continue
                
                # Ignore hidden/system folders
                if current_path.name.startswith(".") or current_path.name.lower() in self.ignore_folders:
                    dirs[:] = []
                    continue
                
                # Prevent recursion into nested system folders
                if depth > 0 and current_path.name.lower() in scan_root_names:
                    dirs[:] = []
                    continue
                
                # Index folder (skip roots themselves)
                if depth > 0:
                    discovered.append(str(current_path))
        
        return discovered

    def _compute_folder_centroid(self, folder_path: str, model):
        """
        Compute centroid for a folder by sampling its files.
        Only processes files with supported extensions.
        """
        folder = Path(folder_path)
        cluster = self.clusters[folder_path]
        
        # Get supported files (non-recursive, just immediate children)
        files = [
            f for f in folder.iterdir() 
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        
        if not files:
            return
        
        # Sample up to 10 files for centroid computation
        sample_files = files[:10]
        embeddings = []
        
        for file_path in sample_files:
            try:
                # Use enricher to extract text
                ctx = enricher.enrich(file_path)
                if ctx.text and len(ctx.text.strip()) > 20:
                    # Truncate to reasonable length
                    text = ctx.text[:1000]
                    emb = model.encode(text, show_progress_bar=False)
                    embeddings.append(emb)
            except Exception as e:
                logger.debug(f"Atlas: Failed to embed {file_path.name}: {e}")
                continue
        
        if embeddings:
            # Compute centroid as average
            cluster.centroid = np.mean(embeddings, axis=0).astype(np.float32)
            cluster.n_files = len(embeddings)

    def _rebuild_search_index(self):
        """Build numpy matrix for fast similarity search."""
        self._path_index = []
        embeddings = []
        
        for path, cluster in self.clusters.items():
            emb = cluster.get_effective_embedding()
            if emb is not None:
                self._path_index.append(path)
                embeddings.append(emb)
        
        if embeddings:
            self._embedding_matrix = np.vstack(embeddings).astype(np.float32)
        else:
            self._embedding_matrix = None

    def find_best_folder(
        self, 
        file_embedding: np.ndarray = None,
        fallback_text: str = None,
        threshold: float = 0.55
    ) -> Tuple[Optional[Path], float]:
        """
        Find the best matching folder for an incoming file.
        
        Args:
            file_embedding: Pre-computed embedding of file content
            fallback_text: Text to embed if file_embedding not provided (e.g., category name)
            threshold: Minimum similarity score to accept match
            
        Returns:
            (matched_folder_path, confidence_score) or (None, 0.0)
        """
        if self._embedding_matrix is None or len(self._path_index) == 0:
            return None, 0.0
        
        # Get query embedding
        if file_embedding is not None:
            query_vec = np.array(file_embedding, dtype=np.float32)
        elif fallback_text:
            model = model_manager.get_embedding_model()
            query_vec = model.encode(fallback_text)
        else:
            return None, 0.0
        
        # Ensure 1D
        if query_vec.ndim > 1:
            query_vec = query_vec.flatten()
        
        # Cosine similarity (vectors are normalized by sentence-transformers)
        # For non-normalized, we'd need: cos_sim = dot / (norm_a * norm_b)
        similarities = np.dot(self._embedding_matrix, query_vec)
        norms = np.linalg.norm(self._embedding_matrix, axis=1) * np.linalg.norm(query_vec)
        similarities = similarities / (norms + 1e-8)
        
        best_idx = np.argmax(similarities)
        best_score = float(similarities[best_idx])
        
        if best_score >= threshold:
            match_path = self._path_index[best_idx]
            match_name = Path(match_path).name
            logger.info(f"Atlas: Match '{fallback_text or 'embedding'}' → '{match_name}' (score: {best_score:.3f})")
            return Path(match_path), best_score
        
        return None, best_score

    def update_cluster(self, folder_path: Path, file_embedding: np.ndarray):
        """
        Update a folder's centroid after placing a new file.
        Called by ExecutionService after successful move.
        """
        path_str = str(folder_path)
        
        if path_str not in self.clusters:
            # New folder - create cluster
            model = model_manager.get_embedding_model()
            name_emb = model.encode(folder_path.name)
            self.clusters[path_str] = FolderCluster(
                path=path_str,
                name_embedding=name_emb
            )
        
        cluster = self.clusters[path_str]
        cluster.update_centroid(file_embedding)
        
        # Rebuild index and save (could be optimized to batch)
        self._rebuild_search_index()
        self.save()
        
        logger.debug(f"Atlas: Updated cluster '{folder_path.name}' (n={cluster.n_files})")

    def save(self):
        """Persist index to disk."""
        try:
            self.index_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": 2,
                "clusters": {path: c.to_dict() for path, c in self.clusters.items()}
            }
            with open(self.index_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Atlas save failed: {e}")

    def load(self):
        """Load index from disk."""
        try:
            with open(self.index_file, "r") as f:
                data = json.load(f)
            
            version = data.get("version", 1)
            if version < 2:
                logger.info("Atlas: Old index version detected. Rescanning...")
                self.scan()
                return
            
            self.clusters = {
                path: FolderCluster.from_dict(c) 
                for path, c in data.get("clusters", {}).items()
            }
            
            self._rebuild_search_index()
            logger.info(f"Atlas: Loaded {len(self.clusters)} clusters from cache.")
            
        except Exception as e:
            logger.error(f"Atlas load failed: {e}. Rescanning...")
            self.scan()


# Global Instance
atlas = AtlasService()
