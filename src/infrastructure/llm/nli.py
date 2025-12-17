
import os
import time
import numpy as np
import psutil
import threading
from typing import List, Tuple, Dict
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer
import onnxruntime as ort
from src.utils.logger import logger

class NLIClassifier:
    """
    NLI-based classifier using ONNX Runtime.
    Replaces LLM for 'Selection' tasks to save memory and improve accuracy.
    Model: Xenova/nli-deberta-v3-xsmall (or similar quantized)
    """
    def __init__(self):
        self._session = None
        self._tokenizer = None
        self._last_used = 0
        self._load_lock = threading.Lock()
        self.model_id = "Xenova/mobilebert-uncased-mnli"
        self.onnx_filename = "onnx/model_quantized.onnx"
        self.min_ram_mb = 300
        self.input_names = []

    def _load_model(self):
        """Lazy load the ONNX model."""
        if self._session is not None:
            return

        with self._load_lock:
            if self._session is not None:
                return

            try:
                free_mem = psutil.virtual_memory().available / (1024 * 1024)
                if free_mem < self.min_ram_mb:
                    logger.warning(f"Very low RAM ({free_mem:.2f} MB). Loading NLI might risky.")

                logger.info(f"Loading NLI Model: {self.model_id}...")
                
                # 1. Tokenizer
                tokenizer_path = hf_hub_download(repo_id=self.model_id, filename="tokenizer.json")
                self._tokenizer = Tokenizer.from_file(tokenizer_path)
                # Shorter max length and dynamic padding to lower RAM per request
                self._tokenizer.enable_truncation(max_length=256)
                self._tokenizer.enable_padding()

                # 2. ONNX Model
                model_path = hf_hub_download(repo_id=self.model_id, filename=self.onnx_filename)
                sess_options = ort.SessionOptions()
                sess_options.intra_op_num_threads = 2
                self._session = ort.InferenceSession(model_path, sess_options)
                
                # Introspect inputs to decide on token_type_ids
                self.input_names = [i.name for i in self._session.get_inputs()]
                logger.info(f"NLI Model Loaded. Inputs: {self.input_names}")
                self._last_used = time.time()
                
            except Exception as e:
                logger.error(f"Failed to load NLI model: {e}")
                raise e

    def _predict_batch(self, premise: str, hypotheses: List[str]) -> np.ndarray:
        """
        Runs NLI comparison.
        Returns array of entailment scores (one per hypothesis).
        """
        self._load_model()
        self._last_used = time.time()

        pairs = [(premise, h) for h in hypotheses]
        batch_size = 8
        all_logits = []
        
        for i in range(0, len(pairs), batch_size):
            batch_pairs = pairs[i : i + batch_size]
            
            encoded_batch = []
            for p, h in batch_pairs:
                enc = self._tokenizer.encode(p, h)
                encoded_batch.append(enc)
                
            input_ids = np.array([e.ids for e in encoded_batch], dtype=np.int64)
            attention_mask = np.array([e.attention_mask for e in encoded_batch], dtype=np.int64)
            
            inputs = {
                'input_ids': input_ids,
                'attention_mask': attention_mask,
            }
            
            # Contextual handling of token_type_ids
            if 'token_type_ids' in self.input_names:
                inputs['token_type_ids'] = np.array([e.type_ids for e in encoded_batch], dtype=np.int64)
            
            outputs = self._session.run(None, inputs)
            logits = outputs[0] 
            all_logits.append(logits)
            
        final_logits = np.vstack(all_logits)
        
        # Softmax
        exp_logits = np.exp(final_logits - np.max(final_logits, axis=1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
        
        # MobileBERT MNLI: In this specific quantized model, observation shows Index 0 is Entailment.
        # Index 2 appears to be Contradiction.
        entailment_scores = probs[:, 0] 
        
        return entailment_scores

    def reason_placement(self, file_path: str, text_snippet: str, existing_folders: List[str]) -> str:
        if not existing_folders: return "Unknown"
        
        # Improve Premise/Hypothesis
        premise = text_snippet[:1000] # Give more context for base model
        
        # "This file is best categorized as {f}." works better to avoid "arsh" being selected just because it's a name match
        hypotheses = [f"This file is best categorized as {f}." for f in existing_folders]
        
        try:
            scores = self._predict_batch(premise, hypotheses)
            best_idx = np.argmax(scores)
            best_score = scores[best_idx]
            best_folder = existing_folders[best_idx]
            
            logger.info(f"NLI Decision: {best_folder} (Score: {best_score:.2f})")
            
            if best_score > 0.5:
                 return best_folder
            return "Unknown"
                
        except Exception as e:
            logger.error(f"NLI Reasoning failed: {e}")
            return "Unknown"

    def get_category_for_keywords(self, keywords: List[str], existing_folders: List[str]) -> str:
        """
        Categorize based on keywords.
        """
        if not keywords: return "Unknown"
        
        premise = f"This file contains the following keywords: {', '.join(keywords)}."
        # Use "categorized as" to bias towards conceptual categories over simple name matches
        hypotheses = [f"This file is best categorized as {f}." for f in existing_folders]
        
        try:
            scores = self._predict_batch(premise, hypotheses)
            best_idx = np.argmax(scores)
            
            if scores[best_idx] > 0.4:
                return existing_folders[best_idx]
            
            return "Unknown"
        except Exception as e:
            logger.error(f"NLI Keyword classification failed: {e}")
            return "Unknown"

FallbackHandler = NLIClassifier
