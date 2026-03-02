"""Centralized logging for podcast automation."""

import logging

from config import Config


def setup_logger(name: str = "podcast_automation") -> logging.Logger:
    """
    Set up and return a logger with console and file handlers.

    Console: INFO+ level
    File: DEBUG+ level, writes to output/podcast_automation.log

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler (INFO+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (DEBUG+)
    try:
        Config.OUTPUT_DIR.mkdir(exist_ok=True)
        log_path = Config.OUTPUT_DIR / "podcast_automation.log"
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        # If we can't write the log file, just use console
        pass

    return logger


# Module-level logger instance for easy import
logger = setup_logger()
