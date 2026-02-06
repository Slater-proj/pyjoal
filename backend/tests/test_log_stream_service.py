"""
Tests for log_stream_service module
"""
import pytest
import logging
from app.services.log_stream_service import LogHandler, log_handler


class TestLogHandler:
    """Tests for the LogHandler class"""

    def test_init(self):
        handler = LogHandler()
        assert handler.log_queue.maxsize == 1000
        assert handler.recent_logs == []
        assert handler.max_recent == 200

    def test_emit_adds_to_recent(self):
        handler = LogHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        handler.emit(record)
        assert len(handler.recent_logs) == 1
        assert handler.recent_logs[0]["message"] == "Test message"
        assert handler.recent_logs[0]["level"] == "INFO"

    def test_emit_trims_recent_logs(self):
        handler = LogHandler()
        handler.max_recent = 5
        handler.setFormatter(logging.Formatter('%(message)s'))
        for i in range(10):
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg=f"Message {i}", args=(), exc_info=None
            )
            handler.emit(record)
        assert len(handler.recent_logs) == 5
        assert handler.recent_logs[0]["message"] == "Message 5"

    def test_emit_adds_to_queue(self):
        handler = LogHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="Queue test", args=(), exc_info=None
        )
        handler.emit(record)
        assert not handler.log_queue.empty()

    def test_get_recent_logs(self):
        handler = LogHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        for i in range(10):
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg=f"Log {i}", args=(), exc_info=None
            )
            handler.emit(record)
        recent = handler.get_recent_logs(count=3)
        assert len(recent) == 3
        assert recent[0]["message"] == "Log 7"

    def test_get_new_logs(self):
        handler = LogHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        for i in range(3):
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg=f"New {i}", args=(), exc_info=None
            )
            handler.emit(record)
        new_logs = handler.get_new_logs(timeout=0.05)
        assert len(new_logs) == 3

    def test_get_new_logs_empty(self):
        handler = LogHandler()
        new_logs = handler.get_new_logs(timeout=0.05)
        assert len(new_logs) == 0

    def test_log_entry_structure(self):
        handler = LogHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        record = logging.LogRecord(
            name="mylogger", level=logging.ERROR, pathname="", lineno=0,
            msg="Error msg", args=(), exc_info=None
        )
        handler.emit(record)
        entry = handler.recent_logs[0]
        assert "timestamp" in entry
        assert "level" in entry
        assert "logger" in entry
        assert "message" in entry
        assert entry["logger"] == "mylogger"
        assert entry["level"] == "ERROR"

    def test_global_log_handler_exists(self):
        assert log_handler is not None
        assert isinstance(log_handler, LogHandler)
        assert log_handler.level == logging.DEBUG
