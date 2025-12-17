import json
import numpy as np
import os
from pathlib import Path
from typing import List, Tuple, Optional
from sentence_transformers import util
from src.config.settings import settings
from src.utils.logger import logger
from src.infrastructure.embeddings.sentence_transformer import model_manager

class SemanticMemory:
    """
    Long-term memory for Sortify.
    Stores examples of (embedding, category) to allow Few-Shot learning.
    """
    def __init__(self):
        self.memory_file = Path.home() / ".sortify" / "memory.json"
        self.max_entries = 200  # Hard cap to keep RAM flat
        self.max_text_chars = 160  # Avoid bloating serialized memory
        
        # Structure: List of {"text": str, "category": str, "embedding": List[float]}
        # We store 'text' (keywords joined) for debugging/re-indexing if model changes.
        self.data = []
        self.embeddings_cache = None # Tensor
        
        self.load()

    def load(self):
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r") as f:
                    raw_data = json.load(f)
                
                # Proactive Pruning: Only keep entries matching current model dimension
                try:
                    expected_dim = model_manager.get_embedding_model().get_sentence_embedding_dimension()
                    cleaned = []
                    for entry in raw_data:
                        emb = entry.get("embedding")
                        if isinstance(emb, list) and len(emb) == expected_dim:
                            entry["text"] = str(entry.get("text", ""))[: self.max_text_chars]
                            cleaned.append(entry)
                    pruned = len(raw_data) - len(cleaned)
                    if pruned:
                        logger.info(f"Pruned {pruned} invalid memory entries on load.")
                    self.data = cleaned[: self.max_entries]
                    if pruned or len(cleaned) > self.max_entries:
                        self.save()
                except Exception as e:
                    logger.warning(f"Model not ready or check failed during load: {e}. Keeping raw data.")
                    self.data = raw_data[: self.max_entries]

                logger.info(f"Memory loaded: {len(self.data)} examples.")
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")
                self.data = []
        else:
            self.data = []
            
        self._rebuild_index()

    def save(self):
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, "w") as f:
                # We save embeddings as lists for JSON compatibility
                json.dump(self.data, f)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def _rebuild_index(self):
        """Convert list of embeddings to a Tensor for fast search."""
        if not self.data:
            self.embeddings_cache = None
            return

        valid_embeddings = []
        clean_data = []
        pruned = 0
        
        for d in self.data:
            emb = d.get("embedding")
            if isinstance(emb, list) and emb and isinstance(emb[0], (int, float)):
                valid_embeddings.append(emb)
                clean_data.append(d)
            else:
                pruned += 1

        if pruned:
            logger.warning(f"Pruned {pruned} corrupted memory entries during index rebuild.")

        self.data = clean_data[: self.max_entries]  # Enforce cap

        if valid_embeddings:
            try:
                self.embeddings_cache = np.array(valid_embeddings[: self.max_entries], dtype=np.float32)
            except Exception as e:
                logger.error(f"Failed to build memory index: {e}")
                self.embeddings_cache = None
            else:
                if pruned:
                    self.save()
        else:
            self.embeddings_cache = None

    def learn(self, text: str, category: str, embedding: np.ndarray = None):
        """
        Add a new example to memory.
        """
        if embedding is None:
            model = model_manager.get_embedding_model()
            embedding = model.encode(text)

        for entry in self.data:
            if entry["text"] == text and entry["category"] == category:
                return

        # Store as list for JSON
        embedding_list = embedding.tolist() if hasattr(embedding, "tolist") else embedding
        text = str(text)[: self.max_text_chars]
        
        # Enforce size cap (drop oldest)
        if len(self.data) >= self.max_entries:
            self.data = self.data[1:]
        
        self.data.append({
            "text": text,
            "category": category,
            "embedding": embedding_list
        })
        
        self.save()
        self._rebuild_index()
        logger.debug(f"Memory learned: '{text}' -> {category}")

    def recall(self, embedding: np.ndarray, threshold: float = 0.6) -> Tuple[Optional[str], float]:
        """
        KNN Search. Returns (category, score).
        """
        if self.embeddings_cache is None or len(self.data) < 1:
            return None, 0.0

        # Compute cosine similarity against all memories
        # embedding shape: (dim,)
        # cache shape: (N, dim)
        
        # Ensure embedding is 1D array
        query_emb = embedding
        
        try:
            # util.cos_sim expects tensors or ndarrays
            hits = util.cos_sim(query_emb, self.embeddings_cache)[0]
            
            # Find best match
            best_score_idx = np.argmax(hits)
            best_score = hits[best_score_idx].item()
            
            if best_score > threshold:
                category = self.data[best_score_idx]["category"]
                logger.debug(f"Memory recall: Matched '{category}' (Score: {best_score:.2f})")
                return category, best_score
                
        except Exception as e:
            logger.error(f"Memory recall error: {e}")
            
        return None, 0.0

memory = SemanticMemory()
