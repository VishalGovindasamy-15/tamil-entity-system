"""
Logging setup for Tamil Entity Recognition system.
Provides consistent formatted loggers across all modules.
"""
import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_initialized = False


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging with consistent formatting."""
    global _initialized
    if _initialized:
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(numeric_level)
    # Avoid duplicate handlers on reload
    if not root.handlers:
        root.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger with consistent formatting.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    setup_logging()
    return logging.getLogger(name)
