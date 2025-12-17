from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional, Dict
from pathlib import Path
import os

class Settings(BaseSettings):
    # Core Settings
    APP_NAME: str = "Sortify"
    DEBUG: bool = False
    APP_NAME: str = "Sortify"
    DEBUG: bool = False
    DRY_RUN: bool = False
    AUTO_START: bool = True # Whether to skip wizard if configured
    
    # Paths
    WATCH_DIRECTORIES: List[Path] = Field(default_factory=lambda: [Path.home() / "Downloads"])
    CATEGORY_MAP: Dict[str, Path] = Field(default_factory=dict) # User defined category -> path map
    TARGET_DIRECTORY: Optional[Path] = None # Base directory for organization (optional)
    
    SCAN_ROOTS: List[Path] = Field(default_factory=lambda: [Path.home() / "Desktop", Path.home() / "Documents"])
    
    LOG_FILE: Path = Path.home() / ".sortify" / "sortify.log"
    DB_FILE: Path = Path.home() / ".sortify" / "history.json"
    
    MODE: str = "zero-config"
    MODEL_TYPE: str = "local"
    
    LOCAL_MODEL_NAME: str = "all-MiniLM-L6-v2"
    CLASSIFICATION_THRESHOLD: float = 0.10
    
    IGNORE_PATTERNS: List[str] = [".tmp", ".crdownload", ".part", "._*"]
    SENSITIVE_KEYWORDS: List[str] = ["bank", "statement", "tax", "password", "secret"]
    
    CONFIG_FILE: Path = Path.home() / ".sortify" / "config.json"

    class Config:
        env_prefix = "SORTIFY_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @classmethod
    def load_from_json(cls):
        """Load settings from JSON config file if exists."""
        start_defaults = {}
        config_path = Path.home() / ".sortify" / "config.json"
        
        if config_path.exists():
            try:
                import json
                with open(config_path, "r") as f:
                    data = json.load(f)
                    # Convert list of strings back to Path objects where needed
                    if "WATCH_DIRECTORIES" in data:
                        data["WATCH_DIRECTORIES"] = [Path(p) for p in data["WATCH_DIRECTORIES"]]
                    if "CATEGORY_MAP" in data:
                        data["CATEGORY_MAP"] = {k: Path(v) for k, v in data["CATEGORY_MAP"].items()}
                    if "LOG_FILE" in data:
                        data["LOG_FILE"] = Path(data["LOG_FILE"])
                    if "DB_FILE" in data:
                        data["DB_FILE"] = Path(data["DB_FILE"])
                    start_defaults.update(data)
            except Exception as e:
                print(f"Warning: Failed to load config.json: {e}")
        
        return cls(**start_defaults)

# Global settings instance
try:
    settings = Settings.load_from_json()
except Exception:
    settings = Settings()

def save_settings(new_settings: dict):
    """
    Save updated settings to user's JSON config file.
    """
    config_path = settings.CONFIG_FILE
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # helper to serialize paths
    def default_serializer(obj):
        if isinstance(obj, Path):
            return str(obj)
        return str(obj)

    try:
        import json
        
        # Merge with existing file if possible to avoid losing keys we don't know about
        current_data = {}
        if config_path.exists():
             try:
                 with open(config_path, "r") as f:
                     current_data = json.load(f)
             except Exception:
                 pass

        current_data.update(new_settings)

        with open(config_path, "w") as f:
            json.dump(current_data, f, indent=4, default=default_serializer)
            
    except Exception as e:
        print(f"Failed to save settings: {e}")
