"""
SuperAI logging (Phase 1)

Dual output: Rich console + rotating daily file under ~/.superai/logs/
Adapted from codes.md.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

_LOGGERS: dict[str, logging.Logger] = {}


def get_logger(name: str = "superai", level: Optional[str] = None) -> logging.Logger:
    """Return a configured logger (console + file). Safe to call multiple times."""
    if name in _LOGGERS:
        logger = _LOGGERS[name]
        if level:
            logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        return logger

    logger = logging.getLogger(name)
    if logger.handlers:
        _LOGGERS[name] = logger
        return logger

    log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    logger.setLevel(log_level)
    logger.propagate = False

    console_handler = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_path=False,
        console=Console(stderr=True),
    )
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    log_dir = Path.home() / ".superai" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"superai_{datetime.now().strftime('%Y%m%d')}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    logger.addHandler(file_handler)

    _LOGGERS[name] = logger
    return logger


logger = get_logger()
