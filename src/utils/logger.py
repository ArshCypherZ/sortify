import logging
from rich.logging import RichHandler
from pathlib import Path

def setup_logger(name: str = "sortify", log_file: Path = None, level: int = logging.INFO) -> logging.Logger:
    """
    Sets up a structured logger with RichHandler for console and FileHandler for file logs.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Console Handler (Rich)
    console_handler = RichHandler(rich_tracebacks=True, markup=True)
    console_handler.setLevel(level)
    formatter = logging.Formatter("%(message)s", datefmt="[%X]")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (if path provided)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

# Default logger instance
logger = setup_logger()
