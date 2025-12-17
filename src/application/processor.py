import queue
import threading
import time
from pathlib import Path
from src.config.settings import settings
from src.utils.logger import logger
from src.i18n.strings import Strings
from src.infrastructure.filesystem.scanner import scanner
from src.infrastructure.extractors.text import Ingestor
from src.core.classification.keywords import KeywordExtractor

class EventProcessor(threading.Thread):
    def __init__(self, event_queue: queue.Queue):
        super().__init__()
        self.queue = event_queue
        self.running = True
        self.paused = False
        self.ingestor = Ingestor()
        self.extractor = KeywordExtractor()
        
        from src.services.atlas import atlas
        self.atlas = atlas
        self.atlas.initialize() 
        from src.services.pipeline import ProcessingPipeline
        self.pipeline = ProcessingPipeline()

    def pause(self):
        self.paused = True
        logger.info(Strings.PROCESSOR_PAUSED.value)

    def resume(self):
        self.paused = False
        logger.info(Strings.PROCESSOR_RESUMED.value)

    def stop(self):
        self.running = False

    def run(self):
        logger.info(Strings.PROCESSOR_STARTED.value)
        from src.utils.system import resource_guard
        
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            
            if not resource_guard.check():
                time.sleep(1)
                continue
                
            try:
                file_path = self.queue.get(timeout=1.0)
                self.process_file(file_path)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Processor loop error: {e}")

    def process_file(self, file_path: Path):
        """
        Main logic for processing a file.
        """
        try:
            if not file_path.exists():
                logger.warning(f"File not found (moved/deleted?): {file_path}")
                return
            
            # Check if this file was recently moved by us (prevent infinite loop)
            from src.services.executor import executor
            if executor.is_recently_moved(file_path):
                logger.debug(f"Skipping recently moved file: {file_path.name}")
                return
            
            logger.info(f"Processing: {file_path.name}")

            # Checks (Size, Privacy)
            # Battery Check
            from src.utils.system import check_battery_ok
            if not check_battery_ok():
                return
            
            # Size Limit Check (200MB max)
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 200:
                logger.warning(f"File {file_path.name} ({file_size_mb:.2f} MB) exceeds size limit. Using basic extension sort.")
                from src.core.classification.classifier import classifier
                category = classifier.classify_by_extension(file_path)
                result = {"category": category, "method": "size_fallback"}
            else:
                 # Pipeline Execution
                from src.services.pipeline import pipeline
                result = pipeline.process_file(file_path)

            category = result.get("category", "Unknown")
            method = result.get("method", "unknown")
            file_keywords = result.get("keywords", [])
            
            logger.info(f"Classification result for {file_path.name}: {category} (Method: {method})")

            if category == "Unknown" or category == "Unsorted":
                 target_folder = settings.WATCH_DIRECTORIES[0] / "_Needs_Review"
            else:
                # Where does this generic category OR these specific keywords go?
                
                # Keywords (Strongest signal: "Techathon" -> "Hackathon")
                # Category (Weak signal: "Events" -> "Events")
                
                search_query = category
                if file_keywords and len(file_keywords) > 0:
                    valid_kws = [k for k in file_keywords if len(k) > 3][:5]
                    if valid_kws:
                        search_query = " ".join(valid_kws)
                
                file_embedding = result.get("embedding")
                
                target_folder, confidence = self.atlas.find_best_folder(
                    file_embedding=file_embedding,
                    fallback_text=search_query,
                    threshold=0.55
                )
                
                if not target_folder and search_query != category:
                    target_folder, confidence = self.atlas.find_best_folder(
                        file_embedding=file_embedding,
                        fallback_text=category,
                        threshold=0.55
                    )
                
                if target_folder:
                     logger.info(f"Atlas: Route to global folder {target_folder.name}")
                else:
                    from src.infrastructure.llm.nli import FallbackHandler
                    agent = FallbackHandler()
                    
                    # Ask NLI for a best fit category
                    text_snippet = " ".join(file_keywords) if file_keywords else file_path.stem
                    suggested_name = agent.get_category_for_keywords(
                        file_keywords[:10] if file_keywords else [file_path.stem],
                        list(settings.CATEGORY_MAP.keys())
                    )
                    
                    if suggested_name:
                        suggested_name = suggested_name.strip().strip("/\\").replace("/", "_").replace("\\", "_")
                    
                    if suggested_name and suggested_name != "Unknown":
                        existing_match, match_conf = self.atlas.find_best_folder(
                            fallback_text=str(suggested_name), 
                            threshold=0.75
                        )
                        
                        if existing_match:
                            logger.info(f"NLI suggested '{suggested_name}', matched to existing '{existing_match.name}'")
                            target_folder = existing_match
                        else:
                            watch_root = Path(settings.WATCH_DIRECTORIES[0]).resolve()
                            target_folder = watch_root / suggested_name
                            logger.info(f"Creating new folder '{suggested_name}' in {watch_root}")
                    else:
                        watch_root = Path(settings.WATCH_DIRECTORIES[0]).resolve()
                        target_folder = watch_root / category

            # Decision & Action
            from src.services.executor import executor
            if executor.safe_move(file_path, target_folder):
                if hasattr(self, 'ui') and self.ui:
                    if "_Needs_Review" in str(target_folder):
                        self.ui.notify(Strings.NOTIF_TITLE.value, Strings.NOTIF_QUARANTINE.value.format(file_path.name))
                    else:
                        self.ui.notify(Strings.NOTIF_TITLE.value, Strings.NOTIF_MOVED.value.format(file_path.name, category))
                
                # Feedback Loop
                if category != "Unknown" and category != "Unsorted":
                    # We need keywords. They are in 'result' from pipeline.
                    keywords = result.get("keywords", [])
                    if keywords:
                        try:
                            from src.core.classification.classifier import classifier
                            classifier.learn(keywords, category)
                        except Exception as e:
                             # Log but don't crash processing loop
                             logger.warning(f"Feedback learning failed (non-critical): {e}")
            
            logger.info(Strings.PHASE_1_COMPLETE.value.format(file_path.name, category))

        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
