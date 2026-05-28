"""Structured JSON logging configuration for Cloud Run Jobs.

Emit one JSON object per line to stdout, compatible with Cloud Logging.
"""

import json
import logging
import os
import sys
import traceback
from datetime import UTC, datetime

_STD_RECORD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class _StdoutHandler(logging.StreamHandler):
    """Stream handler that always writes to stdout regardless of assignment."""

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, value):
        pass


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON for Cloud Logging compatibility."""

    def format(self, record: logging.LogRecord) -> str:
        """Render *record* as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A single-line JSON string.
        """
        entry: dict = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("ctx_"):
                entry[key[4:]] = value
            elif key not in _STD_RECORD_ATTRS and key not in entry:
                entry[key] = value
        if record.exc_info and record.exc_info[0] is not None:
            entry["exc_info"] = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(entry, default=str)


def configure_logging(level: int | None = None) -> None:
    """Configure the root logger for structured JSON output to stdout.

    Attaches a single StreamHandler with JsonFormatter targeting stdout.
    Is idempotent: repeated calls do not duplicate handlers.
    The log level defaults to INFO and can be overridden via the
    LOG_LEVEL environment variable (case-insensitive).

    Args:
        level: Minimum log level. Defaults to logging.INFO unless
            the LOG_LEVEL environment variable is set.
    """
    if level is None:
        env_level = os.environ.get("LOG_LEVEL", "").upper()
        level = getattr(logging, env_level, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    has_json_handler = any(
        isinstance(h, _StdoutHandler) and isinstance(h.formatter, JsonFormatter)
        for h in root.handlers
    )
    if not has_json_handler:
        handler = _StdoutHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)


def get_logger(name: str, **context: object) -> logging.LoggerAdapter:
    """Return a logger with context attributes pre-attached.

    Context values are stored as ctx_ attributes on the adapter's
    extra dict and emitted as flattened fields in every JSON log line.

    Args:
        name: Logger name, typically ``__name__``.
        **context: Key-value pairs to include in every log entry.

    Returns:
        A LoggerAdapter with context attached.
    """
    extra = {f"ctx_{k}": v for k, v in context.items()}
    return logging.LoggerAdapter(logging.getLogger(name), extra)
