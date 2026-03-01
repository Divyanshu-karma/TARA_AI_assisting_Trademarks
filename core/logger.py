# # core/logger.py

# import logging
# import os


# def setup_logger(name="trademark_engine", level=logging.INFO):
#     os.makedirs("logs", exist_ok=True)

#     logger = logging.getLogger(name)
#     logger.setLevel(level)

#     if not logger.handlers:

#         formatter = logging.Formatter(
#             "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
#         )

#         file_handler = logging.FileHandler("logs/pipeline.log")
#         file_handler.setFormatter(formatter)

#         console_handler = logging.StreamHandler()
#         console_handler.setFormatter(formatter)

#         logger.addHandler(file_handler)
#         logger.addHandler(console_handler)

#     return logger

# core/logger.py
"""
Unified logger for the full USPTO examination pipeline.
Used by both the 1st-half (Pillars 1-3) and 2nd-half (§704.02, §1207, §1209).

Usage:
    from core.logger import setup_logger
    logger = setup_logger(__name__)
    logger.info("Running Pillar 1")
"""

import logging
import sys
from pathlib import Path


LOG_FORMAT  = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_DIR     = Path("logs")
LOG_FILE    = LOG_DIR / "pipeline.log"


def setup_logger(name: str = "trademark_engine") -> logging.Logger:
    """
    Creates and configures a logger that writes to both console and file.

    Args:
        name: Logger name — use __name__ in module files for traceability.

    Returns:
        Configured Logger instance.
    """
    LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger(name)

    # Avoid duplicate handlers on re-import
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # ── Console handler ───────────────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(console)

    # ── File handler ──────────────────────────────────────────────────────────
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(file_handler)
    except OSError:
        # In environments where file logging isn't possible, console only
        pass

    return logger