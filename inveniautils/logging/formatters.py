import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


class CustomFormatter(logging.Formatter):
    """
    Formats a log record as text.

    The default time format is ISO 8601 rather than the logging module
    default.
    """

    converter: Callable[[Optional[float]], time.struct_time] = time.gmtime

    def __init__(
        self, fmt: Optional[str] = None, datefmt: Optional[str] = None, style: str = "%"
    ) -> None:
        """
        Inits CustomFormatter.

        See logging.formatter for a more in-depth explanation of arguments.

        Args:
            fmt: Optional; a format string used to format the log. In the style
                specified by the style argument below.
            datefmt: Optional; the time.strftime format string to use for
                formatting the date.
            style: Optional; the style of formatting to use for the body of the
                log message. Either '%' '{', or '$'. Does not affect the style
                for datefmt.
            validate: Optional; validates that the format is of the correct
                style.
        """
        super(CustomFormatter, self).__init__(fmt=fmt, datefmt=datefmt, style=style)

        # milliseconds and timezone are added. See CustomFormatter.formatTime()
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
        # Mypy confused by time.gmtime because it is written in C.
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
        self, record: logging.LogRecord, additional_metadata: Dict[str, Any] = {}
    ) -> str:
        """
        Formats a log record as text.
        Behaves the same as logging.Formatter.format, but appends any additional
        metadata to the end of the message on new lines.

        Args:
            record: The log record to format.
            additional_metadata: Additional fields and values to add to the
                output.
                All values must have a __str__ representation.
                Does not overwrite default values.
        """
        string: str = super(CustomFormatter, self).format(record)

        if additional_metadata:
            string = string.rstrip()

            items: List[Tuple[str, Any]] = list(additional_metadata.items())
            items.sort(key=lambda x: x[0])

            values: List[str] = [str(x[1]) for x in items]
            values.insert(0, string)
            string = "\n".join(values)

        return string


class CloudWatchLogFormatter(CustomFormatter):
    """Format logs appropriately for delivery to cloudwatch."""

    def format(
        self, record: logging.LogRecord, additional_metadata: Dict[str, Any] = {}
    ) -> str:
        """
        Formats a log record as text amenable to cloudwatch.

        Args:
            record: The log record to format.
            additional_metadata: Additional fields and values to add to the
                output.
                All values must have a __str__ representation.
                Does not overwrite default values.
        """
        # Use "\r" as the line delimiter for log messages sent to CloudWatch
        # logs so that individual lines aren't split into different log events.
        log_string: str = super(CloudWatchLogFormatter, self).format(
            record, additional_metadata
        )
        return "\r".join(log_string.splitlines())


class JSONFormatter(CustomFormatter):
    """
    Formats logs as JSON dictionaries.
    """

    def __init__(self, datefmt: Optional[str] = None) -> None:
        """
        Initializes the formatter.

        Args:
            datefmt: Optional; A strftime format string that determines how the
                timestamp is formatted.
                Default ISO 8601 format.
        """
        super(JSONFormatter, self).__init__(datefmt=datefmt)

    def format(
        self, record: logging.LogRecord, additional_metadata: Dict[str, Any] = {}
    ) -> str:
        """
        Formats a log record into a dictionary, then JSON dumps.

        Args:
            record: The log record to format.
            additional_metadata: Additional fields and values to add to the
                output.
                All values must have a __str__ representation.
                Does not overwrite default values.
        """
        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)

        # Add the default fields to the message.
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

        # Add exception information if it is present.
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted["exception"] = record.exc_text
        if record.stack_info:
            formatted["stack_trace"] = self.formatStack(record.stack_info)

        # Add additional metadata if specified.
        if additional_metadata:
            key: str
            value: Any
            for key, value in additional_metadata.items():
                if key not in formatted:
                    try:
                        formatted[key] = str(value)
                    except Exception:
                        pass

        return json.dumps(formatted)
