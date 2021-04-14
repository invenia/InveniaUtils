import logging
from typing import Any, Dict, List, Tuple, Union

from inveniautils.logging.formatters import CustomFormatter


class CustomHandler(logging.Handler):
    """
    Base custom handler that can add additional metadata to every log it
    handles.

    For additional metadata to appear in logs, a subclass of CustomFormatter
    must be set as the handler's formatter.
    """

    def __init__(
        self, level: int = logging.NOTSET, global_metadata: Dict[str, Any] = None
    ) -> None:
        """
        Inits CustomHandler.

        Args:
            global_metadata: Optional; additional keys and values that will
                appear in every log handled by this handler.
                Every item must have a __str__ representation.
        """
        super(CustomHandler, self).__init__(level=level)

        self.default_formatter: CustomFormatter = CustomFormatter()

        self.global_metadata: Dict[str, Any]
        if global_metadata:
            self.global_metadata = global_metadata
        else:
            self.global_metadata = {}

    def set_global_metadata(self, **kwargs: Any) -> None:
        """
        Sets additional keys and values that will appear in every log handled by
        this handler.
        Every item must have a __str__ representation.
        """
        key: str
        value: Any
        for key, value in kwargs.items():
            self.global_metadata[key] = value

    def find_global_metadata(self, key: str) -> Union[Any, None]:
        """
        Find returns the current value of the global metadata item specified by
        key or returns None should it not exist.
        """
        return self.global_metadata.get(key)

    def list_global_metadata(self) -> List[Tuple[str, Any]]:
        """
        Returns a list of tuples of all the key value pairs that have been
        defined in the global metadata.
        """
        return list(self.global_metadata.items())

    def reset_global_metadata(self) -> None:
        """
        Removes all currently set global metadata items.
        """
        self.global_metadata = {}

    def format(self, record: logging.LogRecord) -> str:
        output: str
        if self.formatter:
            if isinstance(self.formatter, CustomFormatter):
                output = self.formatter.format(
                    record, additional_metadata=self.global_metadata
                )
            else:
                output = self.formatter.format(record)
        else:
            output = self.default_formatter.format(
                record, additional_metadata=self.global_metadata
            )

        return output

    def emit(self, record: logging.LogRecord) -> None:
        """
        Actually log the LogRecord.
        Must be implemented by SubClasses.

        Args:
            record: the record to be logged.
        """
        raise NotImplementedError(
            "emit must be implemented by CustomHandler subclasses"
        )
