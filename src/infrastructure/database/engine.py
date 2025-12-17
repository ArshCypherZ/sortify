from pathlib import Path
from sqlmodel import create_engine, SQLModel, Session
from src.config.settings import settings
from src.utils.logger import logger

DB_DIR = Path.home() / ".sortify"
DB_NAME = "sortify.db"
DB_URL = f"sqlite:///{DB_DIR}/{DB_NAME}"
DB_DIR.mkdir(parents=True, exist_ok=True)
engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})

def init_db():
    try:
        from . import models
        SQLModel.metadata.create_all(engine)
        logger.info(f"Database initialized at {DB_URL}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def get_session():
    return Session(engine)
