import json
import logging
import sys
import types
from typing import Any, Dict, Mapping, Optional, Set, Tuple, Type, Union

import pytest  # type: ignore

import inveniautils.logging


class ComplexObject:
    def __init__(self) -> None:
        pass

    def __eq__(self, other) -> bool:
        return isinstance(other, ComplexObject)


class CustomEncoder(json.JSONEncoder):
    def default(self, obj: Dict[str, str]) -> Union[Dict[str, str], str]:
        if isinstance(obj, ComplexObject):
            return {"_type": "complex_object"}
        else:
            return super().default(obj)


class CustomDecoder(json.JSONDecoder):
    def __init__(self) -> None:
        super().__init__(object_hook=self.object_hook)

    def object_hook(self, obj: Any) -> Any:
        if "_type" in obj and obj["_type"] == "complex_object":
            return ComplexObject()
        else:
            return obj


class TestJSONFormatter:
    @pytest.fixture
    def formatter(self) -> inveniautils.logging.JSONFormatter:
        return inveniautils.logging.JSONFormatter()

    def helper(
        self,
        formatter: inveniautils.logging.JSONFormatter,
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
        custom_encoder: Optional[Type[json.JSONEncoder]] = None,
        custom_decoder: Optional[Type[json.JSONDecoder]] = None,
        additional_metadata: Dict[str, Any] = {},
    ) -> None:
        """
        Creates a log record, runs the formatter, and checks the output.

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
            custom_encoder: Optional; custom encoder for the formatter to use.
            custom_decoder: Optional; custom encoder so that the helper can
                understand the formatter's output.
            additional_metadata: Additional fields to appear in the formatted
                output.
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

        # Format the record and decode the output.
        message_str: str = formatter.format(
            record,
            custom_encoder=custom_encoder,
            additional_metadata=additional_metadata,
        )
        assert isinstance(message_str, str)
        message_dict: Dict[str, Any] = json.loads(message_str, cls=custom_decoder)

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
            assert message_dict[key] == value

    def test_basic(self, formatter: inveniautils.logging.JSONFormatter) -> None:
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

    def test_format_dict(self, formatter: inveniautils.logging.JSONFormatter) -> None:
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

    def test_exception(self, formatter: inveniautils.logging.JSONFormatter) -> None:
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

    def test_additional_kwargs(
        self, formatter: inveniautils.logging.JSONFormatter
    ) -> None:
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

    def test_custom_encoder(
        self, formatter: inveniautils.logging.JSONFormatter
    ) -> None:
        self.helper(
            formatter,
            logger_name="test_logger",
            level=20,
            level_name="INFO",
            test_path="animals/chordaesa/cat.py",
            line_no=8601,
            test_message="meow",
            record_args=(),
            function="meow_repeatedly",
            custom_encoder=CustomEncoder,
            custom_decoder=CustomDecoder,
            additional_metadata={"mental_state": ComplexObject()},
        )
