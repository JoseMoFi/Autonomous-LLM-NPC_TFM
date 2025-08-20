# src/world/logger.py
import logging
import os
from typing import Optional

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def get_logger(name: str,
               file_path: Optional[str] = None,
               level: int = logging.INFO) -> logging.Logger:
    """
    Logger con formateo consistente. Si no se pasa file_path, escribe en logs/world/world.log.
    """
    if file_path is None:
        _ensure_dir("logs/world")
        file_path = os.path.join("logs", "world", "world.log")
    else:
        _ensure_dir(os.path.dirname(file_path))

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # ya configurado

    logger.setLevel(level)
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(file_path, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logger.propagate = False
    return logger
