import io
import json
import logging
import sys
import types
from typing import Any, Dict, Mapping, Optional, Set, Tuple, Type, Union

import pytest  # type: ignore

import inveniautils.logging.formatters as FORMATTERS
from inveniautils.logging.handlers import CustomHandler
from tests.test_logging.utils import ComplexObject, create_record


class TestCustomFormatter:
    @pytest.fixture
    def formatter(self) -> FORMATTERS.CustomFormatter:
        return FORMATTERS.CustomFormatter()

    @pytest.fixture
    def log_parts(self) -> Dict[str, Any]:
        return {
            "logger_name": "test_logger",
            "level": 30,
            "level_name": "WARNING",
            "test_path": "fake_module/test_dir/test.py",
            "line_no": 12345,
            "test_message": "%s %s",
            "record_args": ("test", "message"),
            "function": "fake_func",
        }

    @pytest.fixture
    def record(self, log_parts: Dict[str, Any]) -> logging.LogRecord:
        return create_record(
            log_parts["logger_name"],
            log_parts["level"],
            log_parts["test_path"],
            log_parts["line_no"],
            log_parts["test_message"],
            log_parts["record_args"],
            log_parts["function"],
        )

    def test_basic(
        self,
        formatter: FORMATTERS.CustomFormatter,
        log_parts: Dict[str, Any],
        record: logging.LogRecord,
    ) -> None:
        message_str: str = formatter.format(record)

        assert isinstance(message_str, str)
        assert message_str == "test message"

    def test_formatted(
        self, log_parts: Dict[str, Any], record: logging.LogRecord
    ) -> None:
        formatter: FORMATTERS.CustomFormatter = FORMATTERS.CustomFormatter(
            fmt=(
                "{name}|{levelno}|{levelname}|{pathname}|{filename}|{module}"
                "|{lineno}|{funcName}|{created}|{asctime}|{msecs}|"
                "{relativeCreated}|{message}"
            ),
            style="{",
        )

        message_str: str = formatter.format(record)

        assert isinstance(message_str, str)
        assert message_str == (
            "test_logger|30|WARNING|fake_module/test_dir/test.py|test.py|test|"
            "12345|fake_func|570240000|1988-01-27T00:00:00.023+0000|23|100|"
            "test message"
        )

    def test_exception(
        self, formatter: FORMATTERS.CustomFormatter, log_parts: Dict[str, Any]
    ) -> None:
        try:
            raise BaseException
        except BaseException:
            exc_info: Union[
                Tuple[Type[BaseException], BaseException, types.TracebackType],
                Tuple[None, None, None],
            ] = sys.exc_info()

        record: logging.LogRecord = create_record(
            log_parts["logger_name"],
            log_parts["level"],
            log_parts["test_path"],
            log_parts["line_no"],
            log_parts["test_message"],
            log_parts["record_args"],
            log_parts["function"],
            exc_info=exc_info,
            sinfo="test stacktrace",
        )

        message_str: str = formatter.format(record)

        assert isinstance(message_str, str)
        assert "test message\n" in message_str
        assert "test stacktrace" in message_str
        assert "Traceback (most recent call last):\n" in message_str
        assert "BaseException" in message_str
        assert log_parts["logger_name"] not in message_str

    def test_additional_metadata(
        self,
        formatter: FORMATTERS.CustomFormatter,
        log_parts: Dict[str, Any],
        record: logging.LogRecord,
    ) -> None:
        message_str: str = formatter.format(
            record, additional_metadata={"sloth": ComplexObject(), "bat": "hat"}
        )

        assert isinstance(message_str, str)
        assert message_str == "test message\nhat\notiose"

    def test_formatTime(
        self, formatter: FORMATTERS.CustomFormatter, record: logging.LogRecord
    ) -> None:
        assert formatter.formatTime(record) == "1988-01-27T00:00:00.023+0000"
        assert formatter.formatTime(record, datefmt="%B") == "January"

    def test_standard_handler(
        self,
        formatter: FORMATTERS.CustomFormatter,
        log_parts: Dict[str, Any],
        record: logging.LogRecord,
    ) -> None:
        stream: io.StringIO = io.StringIO()
        handler: logging.Handler = logging.StreamHandler(stream=stream)
        handler.setFormatter(formatter)

        handler.emit(record)
        output: str = stream.getvalue()

        assert output == "test message\n"

    def test_custom_handler(
        self,
        formatter: FORMATTERS.CustomFormatter,
        log_parts: Dict[str, Any],
        record: logging.LogRecord,
    ) -> None:
        handler: CustomHandler = CustomHandler()

        handler.setFormatter(formatter)
        output: str = handler.format(record)

        assert output == "test message"


class TestCloudWatchLogFormatter:
    def test_basic(self) -> None:
        record: logging.LogRecord = create_record(
            "test_logger",
            50,
            "fake/fake_path/fake.py",
            65537,
            "\ntest_\nmessage_%s",
            ("oh_no",),
            "fake_function",
        )

        formatter: FORMATTERS.CloudWatchLogFormatter = (
            FORMATTERS.CloudWatchLogFormatter(
                fmt=("{name}\n{levelno}\n{message}"), style="{"
            )
        )
        message_str: str = formatter.format(
            record, additional_metadata={"ball": "hall", "fall": "gaul"}
        )

        assert isinstance(message_str, str)
        assert message_str == "test_logger\r50\r\rtest_\rmessage_oh_no\rhall\rgaul"


class TestJSONFormatter:
    @pytest.fixture
    def formatter(self) -> FORMATTERS.JSONFormatter:
        return FORMATTERS.JSONFormatter()

    def helper(
        self,
        formatter: FORMATTERS.JSONFormatter,
        logger_name: str,
        level: int,
        level_name: str,
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
        additional_metadata: Dict[str, Any] = {},
    ) -> None:
        """
        Checks the formatter's output against the expected output.

        Args:
            formatter: The JSONFormatter instance to test.
            logger_name: Test variable, name of the fictional logger.
            level: Test variable, fictional numerical severity level.
            level_name: Test variable, fictional severity level name.
            test_path: Test variable, fictional file path.
            line_no: Test variable, fictional line number.
            test_message: Test variable, fictional log message.
            record_args: Test variable, strings to be formatted into
                test_message.
            function: Test variable, fictional calling function name.
            exc_info: Optional; test variable, fictional exception info.
            sinfo: Optional; test variable, fictional stack info.
            additional_metadata: Additional fields to appear in the formatted
                output.
        """
        record: logging.LogRecord = create_record(
            logger_name,
            level,
            test_path,
            line_no,
            test_message,
            record_args,
            function,
            exc_info=exc_info,
            sinfo=sinfo,
        )

        message_str: str = formatter.format(
            record, additional_metadata=additional_metadata
        )
        assert isinstance(message_str, str)
        # Decode the output.
        message_dict: Dict[str, Any] = json.loads(message_str)

        # A set of all the keys that should appear in the formatted log.
        expected_keys: Set[str] = set(
            [
                "timestamp",
                "report",
                "logger",
                "level",
                "level_num",
                "function",
                "line",
                "path",
            ]
        )
        expected_keys.update(additional_metadata.keys())
        if exc_info is not None:
            expected_keys.add("exception")
        if sinfo is not None:
            expected_keys.add("stack_trace")

        # Check that the expected keys appear in the formatted log.
        assert set(message_dict.keys()) == expected_keys  # type: ignore

        # Check that the value of the keys is what we expect.
        assert message_dict["timestamp"] == "1988-01-27T00:00:00.023+0000"
        assert message_dict["logger"] == logger_name
        assert message_dict["level_num"] == level
        assert message_dict["level"] == level_name
        assert message_dict["path"] == test_path
        assert message_dict["line"] == line_no
        assert message_dict["report"] == record.getMessage()
        assert message_dict["function"] == function

        # Check any additional metadata fields passed to the formatter.
        key: str
        value: Any
        for key, value in additional_metadata.items():
            assert message_dict[key] == str(value)

    def test_basic(self, formatter: FORMATTERS.JSONFormatter) -> None:
        self.helper(
            formatter,
            logger_name="format_test_logger",
            level=30,
            level_name="WARNING",
            test_path="test_dir/test.py",
            line_no=999,
            test_message="%s %s",
            record_args=("test", "message"),
            function="test_func",
        )

    def test_format_dict(self, formatter: FORMATTERS.JSONFormatter) -> None:
        self.helper(
            formatter,
            logger_name="sefhzkslbf",
            level=50,
            level_name="CRITICAL",
            test_path="/badly/formatted/stuffeSEIOFGS//\\/.235#$%32.4245238",
            line_no=6,
            test_message={"this": "is", "a": 60},
            record_args=(),
            function="garbage_function",
        )

    def test_exception(self, formatter: FORMATTERS.JSONFormatter) -> None:
        try:
            raise BaseException
        except BaseException:
            self.helper(
                formatter,
                logger_name="good_logger",
                level=40,
                level_name="ERROR",
                test_path="test_dir/test.py",
                line_no=38,
                test_message="uh oh",
                record_args=(),
                function="garbage_function",
                exc_info=sys.exc_info(),
                sinfo="this is a stacktrace:\nyup",
            )

    def test_additional_kwargs(self, formatter: FORMATTERS.JSONFormatter) -> None:
        self.helper(
            formatter,
            logger_name="test_logger",
            level=10,
            level_name="DEBUG",
            test_path="animals/molluscs/nudibranch.py",
            line_no=6174,
            test_message="Target sponge is getting away!",
            record_args=(),
            function="eat_sponge",
            additional_metadata={
                "sensory_organs": ["eyes", "rhinophores"],
                "cute": True,
            },
        )

    def test_custom_object(self, formatter: FORMATTERS.JSONFormatter) -> None:
        self.helper(
            formatter,
            logger_name="test_logger",
            level=20,
            level_name="INFO",
            test_path="animals/chordates/cat.py",
            line_no=8601,
            test_message="meow",
            record_args=(),
            function="meow_repeatedly",
            additional_metadata={"mental_state": ComplexObject()},
        )

    def test_standard_handler(self, formatter: FORMATTERS.JSONFormatter) -> None:
        record: logging.LogRecord = create_record(
            "test_logger", 30, "ugh/woops.py", 1729, "test message", (), "test_function"
        )
        stream: io.StringIO = io.StringIO()
        handler: logging.Handler = logging.StreamHandler(stream=stream)

        handler.emit(record)
        output: str = stream.getvalue()

        assert "test message" in output

    def test_custom_handler(self, formatter: FORMATTERS.JSONFormatter) -> None:
        record: logging.LogRecord = create_record(
            "test_logger", 30, "ugh/woops.py", 1729, "test message", (), "test_function"
        )
        handler: CustomHandler = CustomHandler()

        output: str = handler.format(record)

        assert "test message" in output
