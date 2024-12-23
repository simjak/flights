import logging
import sys
from typing import Optional


def get_logger(
    name: str,
    level: Optional[int] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Get a configured logger instance."""
    logger = logging.getLogger(name)

    if level is None:
        level = logging.INFO

    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Only add handler if logger doesn't have handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(format_string))
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False

    return logger
