from typing import List, Dict, Optional, Tuple
from pathlib import Path
from sentence_transformers import util
from src.config.settings import settings
from src.utils.logger import logger
from src.infrastructure.embeddings.sentence_transformer import model_manager

class Classifier:
    def __init__(self):
        self.model = None
        self.categories = {
            "Documents": "Official documents, business letters, contracts, forms, legal papers, memos, administrative records, pdf, txt, docx.",
            "Images": "Photos, pictures, screenshots, wallpapers, graphics, designs, camera rolls, jpg, png, image.",
            "Video": "Movies, screen recordings, films, tv shows, episodes, clips, video footage, mp4, avi, mov.",
            "Audio": "Music, songs, podcasts, voice notes, audiobooks, sound effects, recording, mp3, wav.",
            "Archives": "Compressed zip files, rar, tar, 7z, backups, disk images, archive.",
            "Code": "Programming code, scripts, source files, python, javascript, html, css, java, react, django, api, backend, frontend, def, class, import, function, return, var, const, let, database, sql, git, repo, pipeline.",
            "Finance": "Invoices, receipts, tax returns, bank statements, bills, credit card reports, ledger, salary slips, accounting, money, price, cost, total, amount, pay, purchase.",
            "Academic": "Educational materials, course content, machine learning, artificial intelligence, neural networks, deep learning, supervised learning, unsupervised learning, lectures, tutorials, study guides, textbooks, research, algorithms, data science, statistics, training, model, classification, regression.",
            "College": "University administrative documents, syllabus, semester schedules, exam papers, assignments, practicals, labs, thesis, research projects, student enrollment, course registration, professor, grade, GPA.",
            "Personal": "Family photos, private letters, medical records, id cards, passport, visa, personal journal, diary, health, insurance.",
            "Projects": "Project source code, hackathon deliverables, development builds, technical specifications, repository data, readme, design doc, architecture.",
            "Events": "Event tickets, conference schedules, meetup invites, workshop materials, calendar entries, rsvp, booking.",
        }
        self.extensions = {
            "Documents": ["pdf", "docx", "txt", "md"],
            "Images": ["jpg", "jpeg", "png", "gif", "svg"],
            "Video": ["mp4", "mkv", "mov", "avi"],
            "Audio": ["mp3", "wav", "flac"],
            "Archives": ["zip", "rar", "tar", "gz"],
            "Code": ["py", "js", "html", "css", "java", "cpp"],
            "Finance": ["invoice", "receipt", "bank", "statement", "tax"],
            "College": ["syllabus", "assignment", "lecture", "notes", "exam"],
            "Personal": ["photo", "family", "vacation"],
        }
        self.category_embeddings = {}
        self._initialized = False

    def _ensure_initialized(self):
        if not self._initialized:
            self.model = model_manager.get_embedding_model()
            logger.info("Computing category embeddings...")
            for cat, description in self.categories.items():
                self.category_embeddings[cat] = self.model.encode(description)
            self._initialized = True
            
    def update_dynamic_categories(self, discovered_map: Dict[str, Path]):
        self._ensure_initialized()
        
        for category, path in discovered_map.items():
            if category not in self.category_embeddings:
                desc = category.replace("_", " ").replace("-", " ")
                logger.debug(f"Embedding dynamic category: {category}")
                try:
                    self.category_embeddings[category] = self.model.encode(desc)
                except Exception as e:
                    logger.warning(f"Failed to embed {category}: {e}")

    def classify_by_extension(self, file_path: Path) -> str:
        ext = file_path.suffix.lower().lstrip(".")
        for cat, exts in self.extensions.items():
            if ext in exts:
                return cat
        return "Unknown"

    def classify_by_keywords(self, keywords: List[str]) -> Tuple[str, float]:
        if not keywords:
            return "Unknown", 0.0
        
        try:
            self._ensure_initialized()
            query_text = " ".join(keywords)
            query_embedding = self.model.encode(query_text)
            
            from src.services.memory import memory
            mem_cat, mem_score = memory.recall(query_embedding, threshold=0.75)
            if mem_cat:
                return mem_cat, mem_score

            best_cat = "Unknown"
            best_score = -1.0
            
            for cat, cat_embedding in self.category_embeddings.items():
                score = util.cos_sim(query_embedding, cat_embedding).item()
                if score > best_score:
                    best_score = score
                    best_cat = cat
            
            logger.debug(f"Best match for '{query_text}': {best_cat} (Score: {best_score:.2f})")
            if best_score < settings.CLASSIFICATION_THRESHOLD:
                logger.info(f"Classification score {best_score:.2f} below threshold for {best_cat}")
                return "Unknown", best_score
                
            return best_cat, best_score

        except Exception as e:
            logger.error(f"Vector classification failed: {e}")
            return "Unknown", 0.0

    def find_best_match(self, query: str, candidates: List[str], keywords: List[str] = None) -> Optional[str]:
        """
        Hybrid Ensemble Matching:
        1. Direct Entity Match: Checks if file keywords match a folder name (e.g., "preply" -> "preply").
        2. Semantic Match: Vectors (e.g., "Images" -> "Pictures").
        """
        if not candidates:
            return None

        if keywords:
            normalized_candidates = {c.lower(): c for c in candidates}
            for kw in keywords:
                kw_clean = kw.lower().strip(".,-_")
                if kw_clean in normalized_candidates:
                    logger.info(f"Ensemble: Direct Keyword Match '{kw}' -> '{normalized_candidates[kw_clean]}'")
                    return normalized_candidates[kw_clean]

        try:
            self._ensure_initialized()
            query_embedding = self.model.encode(query)
            
            best_candidate = None
            best_score = -1.0
            
            for cand in candidates:
                if cand in self.category_embeddings:
                    cand_embedding = self.category_embeddings[cand]
                else:
                    cand_embedding = self.model.encode(cand.replace("_", " "))
                    
                score = util.cos_sim(query_embedding, cand_embedding).item()
                
                if score > best_score:
                    best_score = score
                    best_candidate = cand
            
            logger.debug(f"Ensemble: Semantic Match '{query}' -> '{best_candidate}' (Score: {best_score:.2f})")
            
            if best_score > 0.75:
                return best_candidate
                
            return None
            
        except Exception as e:
            logger.error(f"Semantic match failed: {e}")
            return None

    def learn(self, keywords: List[str], category: str):
        if not keywords or category == "Unknown":
            return
            
        try:
            self._ensure_initialized()
            text = " ".join(keywords)
            embedding = self.model.encode(text)
            from src.services.memory import memory
            memory.learn(text, category, embedding)
        except Exception as e:
            logger.error(f"Failed to learn: {e}")

classifier = Classifier()
