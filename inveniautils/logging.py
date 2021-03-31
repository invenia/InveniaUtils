import json
import logging
import time
from typing import Any, Callable, Dict, Optional, Type


class JSONFormatter(logging.Formatter):
    """
    Formats logs as JSON dictionaries.
    """

    # No type hint because time is C and confuses Mypy
    converter: Callable[[Optional[float]], time.struct_time] = time.gmtime

    def __init__(self, datefmt: Optional[str] = None) -> None:
        """
        Initializes the formatter.

        Args:
            datefmt: Determines how the timestamp is formatted.
                Default ISO 8601.
        """
        super(JSONFormatter, self).__init__(fmt=None, datefmt=datefmt, style="%")

        # milliseconds and timezone are added. See JSONFormatterformatTime()
        self.default_time_format: str = "%Y-%m-%dT%H:%M:%S"

    def formatTime(self, record: logging.LogRecord, datefmt: str = None) -> str:
        """
        Return the creation time of the specified LogRecord as formatted text.

        If datefmt is specified, creation time is formatted using time.strftime.
        Default format follows ISO 8601 with milliseconds and timezone.
        Args:
            record: The log record being formatted.
            datefmt: Optional; strftime format to use.
        """
        # Mypy confused by time.gmtime because it is written in C and does not
        # accept self.
        ct: time.struct_time = self.converter(record.created)  # type: ignore

        formatted: str
        if datefmt:
            formatted = time.strftime(datefmt, ct)
        else:
            formatted = (
                f"{time.strftime(self.default_time_format, ct)}"
                f".{record.msecs:03.0f}{time.strftime('%z', ct)}"
            )
        return formatted

    def format(
        self,
        record: logging.LogRecord,
        custom_encoder: Optional[Type[json.JSONEncoder]] = None,
        additional_metadata: Dict[str, Any] = {},
    ) -> str:
        """
        Formats a log record into a dictionary, then JSON dumps.

        Args:
            record: The log record to format.
            custom_encoder: A custom JSON encoder to use when encoding.
            additional_metadata: Additional fields and values to add to the
                output.
                Must be JSON compatible or handled by the custom_encoder.
                Does not overwrite default values.
        """
        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)

        formatted: Dict[str, Any] = {
            "timestamp": record.asctime,
            "report": record.message,
            "logger": record.name,
            "level": record.levelname,
            "level_num": record.levelno,
            "function": record.funcName,
            "line": record.lineno,
            "path": record.pathname,
        }

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted["exception"] = record.exc_text
        if record.stack_info:
            formatted["stack_trace"] = self.formatStack(record.stack_info)

        key: str
        value: Any
        for key, value in additional_metadata.items():
            if key not in formatted:
                formatted[key] = value

        return json.dumps(formatted, cls=custom_encoder)
