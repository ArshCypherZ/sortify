
import os
import time
import numpy as np
from pathlib import Path
from typing import List, Union
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer
import onnxruntime as ort
import threading
from src.utils.logger import logger

class ModelManager:
    def __init__(self):
        self._session = None
        self._tokenizer = None
        self._last_used = 0
        self._load_lock = threading.Lock()
        self.keep_alive_seconds = 60
        self.model_id = "Xenova/all-MiniLM-L6-v2"
        self.onnx_filename = "onnx/model_quantized.onnx" 
        self._input_names = set()

    def get_sentence_embedding_dimension(self) -> int:
        return 384

    def _load_model(self):
        """Thread-safe lazy loader to avoid concurrent heavy inits."""
        if self._session is not None:
            return

        with self._load_lock:
            if self._session is not None:
                return

            try:
                logger.info(f"Loading ONNX Model: {self.model_id}...")
                
                tokenizer_path = hf_hub_download(repo_id=self.model_id, filename="tokenizer.json")
                self._tokenizer = Tokenizer.from_file(tokenizer_path)
                # Dynamic padding avoids allocating 512 tokens for every short string
                self._tokenizer.enable_truncation(max_length=512)
                self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")

                model_path = hf_hub_download(repo_id=self.model_id, filename=self.onnx_filename)
                
                sess_options = ort.SessionOptions()
                sess_options.intra_op_num_threads = 1 # Single thread is enough for bg task, saves CPU contention
                self._session = ort.InferenceSession(model_path, sess_options)
                self._input_names = {i.name for i in self._session.get_inputs()}
                
                logger.info("ONNX Model Loaded Successfully.")
                self._last_used = time.time()
                
            except Exception as e:
                logger.error(f"Failed to load ONNX model: {e}")
                raise e

    def unload_model(self):
        if self._session:
            logger.info("Unloading ONNX model to save RAM.")
            self._session = None
            self._tokenizer = None
            import gc
            gc.collect() # Force cleanup

    def get_embedding_model(self):
        return self

    def encode(self, sentences: Union[str, List[str]], batch_size: int = 32, show_progress_bar: bool = False, convert_to_numpy: bool = True) -> Union[List[np.ndarray], np.ndarray]:
        if isinstance(sentences, str):
            sentences = [sentences]
            
        self._load_model()
        self._last_used = time.time()

        all_embeddings = []
        
        # Batch processing
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i : i + batch_size]
            encoded = self._tokenizer.encode_batch(batch)
            
            # Prepare inputs for ONNX
            input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
            attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
            inputs = {
                'input_ids': input_ids,
                'attention_mask': attention_mask,
            }

            if 'token_type_ids' in self._input_names:
                inputs['token_type_ids'] = np.array([e.type_ids for e in encoded], dtype=np.int64)
            
            # Run Inference
            outputs = self._session.run(None, inputs)
            last_hidden_state = outputs[0]
            input_mask_expanded = np.expand_dims(attention_mask, -1)
            
            sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)
            sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
            
            embeddings = sum_embeddings / sum_mask
            
            # Normalize embeddings
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / np.clip(norms, a_min=1e-9, a_max=None)
            
            all_embeddings.append(embeddings)

        # Concatenate batches
        final_embeddings = np.vstack(all_embeddings)
        
        return final_embeddings

model_manager = ModelManager()
