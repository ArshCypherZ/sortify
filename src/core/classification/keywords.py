import numpy as np
import re
from typing import List
from src.utils.logger import logger
from src.infrastructure.embeddings.sentence_transformer import model_manager


# Lightweight, zero-allocation stopword set to keep memory flat
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "at", "is", "are",
    "this", "that", "with", "by", "from", "as", "it", "be", "was", "were", "will", "can",
    "has", "have", "had", "not", "no", "but", "if", "then", "so", "we", "you", "your"
}


class KeywordExtractor:
    def __init__(self):
        # Reuse the ONNX embedder directly to avoid loading a torch SentenceTransformer
        self._embedder = model_manager.get_embedding_model()

    def _tokenize(self, text: str) -> List[str]:
        return [w for w in re.findall(r"[A-Za-z0-9]{3,}", text.lower()) if w not in STOPWORDS]

    def _candidates(self, words: List[str]) -> List[str]:
        # Build unigrams + bigrams, keep ordering while deduping
        unigrams = words
        bigrams = [" ".join(pair) for pair in zip(words, words[1:])]
        ordered = []
        seen = set()
        for token in unigrams + bigrams:
            if token not in seen:
                ordered.append(token)
                seen.add(token)
        return ordered

    def extract(self, text: str, top_n: int = 5) -> List[str]:
        """Memory-lean keyword extraction using cosine to the document embedding."""
        if not text or len(text.strip()) < 5:
            return []

        try:
            words = self._tokenize(text)
            if not words:
                return []

            candidates = self._candidates(words)
            # Cap to keep batch small and RAM bounded
            candidates = candidates[:80]

            doc_text = " ".join(words[:120])
            doc_emb = np.array(self._embedder.encode(doc_text), dtype=np.float32).flatten()
            cand_embs = np.array(self._embedder.encode(candidates, batch_size=16), dtype=np.float32)

            if cand_embs.ndim == 1:
                cand_embs = cand_embs.reshape(1, -1)

            # Cosine similarity doc vs candidates
            doc_norm = np.linalg.norm(doc_emb) + 1e-8
            cand_norm = np.linalg.norm(cand_embs, axis=1) + 1e-8
            scores = (cand_embs @ doc_emb) / (cand_norm * doc_norm)

            # Pick top_n with highest scores
            top_indices = np.argsort(-scores)[:top_n]
            return [candidates[i] for i in top_indices]

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
