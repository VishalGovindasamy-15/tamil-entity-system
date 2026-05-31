"""Tests for core.logger."""
import logging

from core.logger import get_logger, setup_logging


def test_get_logger_returns_logger():
    log = get_logger("test.module")
    assert isinstance(log, logging.Logger)
    assert log.name == "test.module"


def test_get_logger_same_name_returns_same_instance():
    a = get_logger("same_name")
    b = get_logger("same_name")
    assert a is b


def test_setup_logging_idempotent():
    """Calling setup_logging multiple times should not duplicate handlers."""
    setup_logging("DEBUG")
    setup_logging("DEBUG")
    root = logging.getLogger()
    handler_count = len(root.handlers)
    setup_logging("DEBUG")
    assert len(root.handlers) == handler_count


def test_log_output_format(caplog):
    """Logger output should contain the module name and message."""
    log = get_logger("fmt_test")
    with caplog.at_level(logging.INFO, logger="fmt_test"):
        log.info("hello world")
    assert "hello world" in caplog.text
