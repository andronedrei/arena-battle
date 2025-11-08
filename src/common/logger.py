import logging
import os
import datetime
import multiprocessing
from typing import Optional


def setup_logging(app_name: str = "arena-battle", logs_dir: str = "logs") -> logging.Logger:
    """Configure root logger to write to a per-run file under `logs/` and to console.

    Returns the root logger.
    """
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pid = multiprocessing.current_process().pid
    filename = f"{app_name}_{timestamp}_{pid}.log"
    filepath = os.path.join(logs_dir, filename)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear existing handlers to avoid duplicate logs in long-running sessions
    if logger.handlers:
        for h in list(logger.handlers):
            logger.removeHandler(h)

    # File handler
    fh = logging.FileHandler(filepath, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter("%(levelname)s [%(name)s] %(message)s")
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    logger.info("Logging initialized, file=%s", filepath)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger with the given name or the root logger."""
    return logging.getLogger(name)
