import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor

from src.config.settings import settings
from src.utils.logger import logger
from src.services.enrichment import enricher
from src.core.models import FileContext
from src.infrastructure.embeddings.sentence_transformer import model_manager
from src.core.classification.voters import (
    FileTypeVoter, 
    SemanticVoter, 
    HistoryVoter, 
    NLIVoter,
    SessionVoter
)
from src.services.clustering import session_manager

class VotingEngine:
    """
    Core classification engine that combines multiple voting strategies.
    """
    def __init__(self):
        # Initialize Voters (removed TemporalVoter - was always Unknown)
        self.voters = [
            FileTypeVoter(),
            SemanticVoter(),
            HistoryVoter(),
            SessionVoter()
        ]
        self.nli_voter = NLIVoter()
        self.thread_pool = ThreadPoolExecutor(max_workers=2)  # Lower concurrency to reduce peak RAM

    def process_file(self, file_path: Path) -> dict:
        start_time = time.time()
        logger.info(f"Processing {file_path.name}")
        
        # 1. Extract and enrich file metadata
        context = enricher.enrich(file_path)
        
        # 1.5 Compute file embedding for Atlas cluster matching
        file_embedding = None
        if context.text and len(context.text.strip()) > 20:
            try:
                model = model_manager.get_embedding_model()
                file_embedding = model.encode(context.text[:512])
            except Exception as e:
                logger.debug(f"Failed to compute file embedding: {e}")
        
        # 2. Fast Voting (Parallel)
        futures = {self.thread_pool.submit(v.vote, context): v for v in self.voters}
        
        votes = []
        for future in futures:
            voter = futures[future]
            try:
                cat, conf = future.result()
                if cat != "Unknown":
                    votes.append((voter, cat, conf))
            except Exception as e:
                logger.error(f"Voter {voter.name} failed: {e}")

        # 3. Arbitration
        winner, confidence, score_map = self._arbitrate(votes)
        
        # 4. Deep Inspection (NLI fallback)
        method = "voting_ensemble"
        
        # Lowered threshold for NLI to be more active if unsure
        NLI_THRESHOLD = 0.60
        
        if (winner == "Unknown" or confidence < NLI_THRESHOLD) and context.text:
            logger.info(f"Confidence {confidence:.2f}. Using NLI fallback...")
            nli_cat, nli_conf = self.nli_voter.vote(context)
            
            if nli_cat != "Unknown":
                # Add NLI as another voter and RE-ARBITRATE
                votes.append((self.nli_voter, nli_cat, nli_conf))
                winner, confidence, score_map = self._arbitrate(votes)
                method = "voting_ensemble_with_nli"

        # 5. Learning (Session Context)
        if winner != "Unknown":
            session_manager.add_event(str(file_path), winner)

        result = {
            "file_path": str(file_path),
            "category": winner,
            "confidence": confidence,
            "method": method,
            "keywords": list(context.metadata.keys()) + context.text.split()[:10],
            "embedding": file_embedding.tolist() if file_embedding is not None else None,
            "processing_time": time.time() - start_time,
            "votes": [{"voter": v.name, "category": c, "confidence": s} for v, c, s in votes]
        }
        
        return result

    def _arbitrate(self, votes: List[Tuple[object, str, float]]) -> Tuple[str, float, Dict]:
        """
        Calculates weighted scores for all candidates.
        Score = Sum(Voter_Weight * Vote_Confidence)
        """
        if not votes:
            return "Unknown", 0.0, {}
            
        scoreboard = {}
        total_weight_participated = 0.0
        
        for voter, category, confidence in votes:
            if category not in scoreboard:
                scoreboard[category] = 0.0
            
            # Weighted Score
            score = voter.weight * confidence
            scoreboard[category] += score
            
            # This is a bit simplistic, but works for "Winner takes all"
            
        if not scoreboard:
            return "Unknown", 0.0, {}
            
        # Find Winner
        winner = max(scoreboard, key=scoreboard.get)
        raw_score = scoreboard[winner]
        final_confidence = min(raw_score, 1.0)
        return winner, final_confidence, scoreboard

pipeline = VotingEngine()
ProcessingPipeline = VotingEngine

def run_pipeline_task(path: Path) -> dict:
    return pipeline.process_file(path)
