"""Tests for the logging_config module in the hgnc-coord-builder service."""

import json
import logging

import pytest

from hgnc_coord_builder.logging_config import configure_logging, get_logger


class TestJsonFormatterOutput:
    def test_log_line_is_valid_json(self, capsys):
        configure_logging()
        logger = logging.getLogger("test_json")
        logger.info("hello world")
        captured = capsys.readouterr()
        line = captured.out.strip().split("\n")[-1]
        parsed = json.loads(line)
        assert isinstance(parsed, dict)

    def test_log_line_has_severity(self, capsys):
        configure_logging()
        logger = logging.getLogger("test_severity")
        logger.info("test")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip().split("\n")[-1])
        assert parsed["severity"] == "INFO"

    def test_log_line_has_message(self, capsys):
        configure_logging()
        logger = logging.getLogger("test_message")
        logger.info("my test message")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip().split("\n")[-1])
        assert parsed["message"] == "my test message"

    def test_log_line_has_logger(self, capsys):
        configure_logging()
        logger = logging.getLogger("test_logger_name")
        logger.info("test")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip().split("\n")[-1])
        assert parsed["logger"] == "test_logger_name"

    def test_log_line_has_time(self, capsys):
        configure_logging()
        logger = logging.getLogger("test_time")
        logger.info("test")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip().split("\n")[-1])
        assert "time" in parsed
        assert "+00:00" in parsed["time"] or "Z" in parsed["time"]


class TestContextFields:
    def test_ctx_fields_stripped_and_included(self, capsys):
        logger = get_logger("test_ctx", source="uniprot", rows=100)
        logger.info("processed")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip().split("\n")[-1])
        assert parsed["source"] == "uniprot"
        assert parsed["rows"] == 100
        assert "ctx_source" not in parsed

    def test_ctx_fields_in_every_log_line(self, capsys):
        logger = get_logger("test_ctx_multi", job="load")
        logger.info("step 1")
        logger.info("step 2")
        captured = capsys.readouterr()
        lines = [l for l in captured.out.strip().split("\n") if l]
        for line in lines:
            parsed = json.loads(line)
            assert parsed["job"] == "load"


class TestExceptionLogging:
    def test_exception_includes_exc_info(self, capsys):
        logger = logging.getLogger("test_exc")
        configure_logging()
        try:
            raise ValueError("boom")
        except ValueError:
            logger.exception("something failed")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip().split("\n")[-1])
        assert parsed["severity"] == "ERROR"
        assert "exc_info" in parsed
        assert "ValueError" in parsed["exc_info"]
        assert "boom" in parsed["exc_info"]


class TestConfigureLoggingIdempotent:
    def test_no_duplicate_handlers(self):
        root = logging.getLogger()
        initial_count = len(root.handlers)
        configure_logging()
        count_after_first = len(root.handlers)
        configure_logging()
        count_after_second = len(root.handlers)
        assert count_after_first == count_after_second


class TestLogLevels:
    def test_default_level_is_info(self):
        configure_logging()
        root = logging.getLogger()
        assert root.level <= logging.INFO

    def test_log_level_env_var_override(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        configure_logging()
        root = logging.getLogger()
        assert root.level <= logging.DEBUG

    def test_log_level_env_var_warning(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        configure_logging()
        root = logging.getLogger()
        assert root.level <= logging.WARNING

    def test_log_level_env_var_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "debug")
        configure_logging()
        root = logging.getLogger()
        assert root.level <= logging.DEBUG


class TestSeverityMapping:
    @pytest.mark.parametrize("level,expected", [
        (logging.DEBUG, "DEBUG"),
        (logging.INFO, "INFO"),
        (logging.WARNING, "WARNING"),
        (logging.ERROR, "ERROR"),
        (logging.CRITICAL, "CRITICAL"),
    ])
    def test_severity_mapping(self, capsys, level, expected):
        configure_logging(level=logging.DEBUG)
        logger = logging.getLogger(f"test_sev_{expected}")
        logger.log(level, "test")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip().split("\n")[-1])
        assert parsed["severity"] == expected


class TestGetLogger:
    def test_get_logger_returns_logger(self):
        logger = get_logger("test_get")
        assert logger is not None

    def test_get_logger_with_context(self, capsys):
        logger = get_logger("test_get_ctx", source="pdb")
        logger.info("loaded")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out.strip().split("\n")[-1])
        assert parsed["source"] == "pdb"
