import logging
import types
from typing import Any, Mapping, Optional, Tuple, Type, Union


class ComplexObject:
    def __init__(self) -> None:
        pass

    def __str__(self) -> str:
        return "otiose"


def create_record(
    logger_name: str,
    level: int,
    test_path: str,
    line_no: int,
    test_message: Any,
    record_args: Union[Tuple[Any, ...], Mapping[str, Any]],
    function: str,
    exc_info: Optional[
        Union[
            Tuple[Type[BaseException], BaseException, types.TracebackType],
            Tuple[None, None, None],
        ]
    ] = None,
    sinfo: Optional[str] = None,
) -> logging.LogRecord:
    """
    Args:
        logger_name: Name of the fictional logger.
        level: Fictional numerical severity level.
        test_path: Fictional file path.
        line_no: Fictional line number.
        test_message: Fictional log message.
        record_args: Strings to be formatted into test_message.
        function: Fictional calling function name.
        exc_info: Optional; fictional exception info.
        sinfo: Optional; fictional stack info.
    """
    record: logging.LogRecord = logging.LogRecord(
        logger_name,
        level,
        test_path,
        line_no,
        test_message,
        args=record_args,
        exc_info=exc_info,
        func=function,
        sinfo=sinfo,
    )

    # Forge the log record's creation date.
    record.created = 570240000
    record.msecs = 23
    record.relativeCreated = 100

    return record
