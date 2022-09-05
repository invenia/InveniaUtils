import csv
import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import StringIO

import inveniautils.timestamp as timestamp
from inveniautils.timestamp import to_datetime
from inveniautils.to_str import float_to_decimal_str

BOUNDS = {(0, 0): 0, (1, 0): 1, (0, 1): 2, (1, 1): 3}

logger = logging.getLogger(__name__)


class NormalizedWriter(object):
    def __init__(self):
        self.string_buffer = StringIO()
        self.writer = csv.writer(self.string_buffer)
        self.header = []

    def write(self, parsed_row):
        if not self.header:
            self.write_header(parsed_row)

        to_write = []
        row = self.prepare_row(parsed_row)
        for key in self.header:
            value = self.encode_value(row[key])
            to_write.append(value)
        self.writer.writerow(to_write)

    def write_header(self, parsed_row):
        if self.header:
            logger.warning("Writing header more than once, rewriting header!")

        row = self.prepare_row(parsed_row)
        self.header = [key for key in row]
        # self.header.remove("target_range")
        self.writer.writerow(self.header)

    def prepare_row(self, parsed_row):
        row = parsed_row.copy()
        # Split target_range to start, end and bound fields
        target_range = row.pop("target_range")

        row["target_start"] = target_range.start
        row["target_end"] = target_range.end
        row["target_bounds"] = BOUNDS[target_range.bounds]

        return row

    @staticmethod
    def encode_value(value):
        if isinstance(value, datetime):
            # convert all dates to UTC
            result = str(timestamp.from_datetime(value))
        elif isinstance(value, timedelta):
            result = str(value.total_seconds())
        elif isinstance(value, date):
            result = str(value.isoformat())
        elif isinstance(value, bool):
            result = str(int(value))
        elif isinstance(value, int):
            result = str(value)
        elif isinstance(value, float):
            result = float_to_decimal_str(value)
        elif isinstance(value, Decimal):
            result = str(value)
        elif isinstance(value, str):
            result = str(value)
        elif isinstance(value, tuple) and isinstance(value[0], str):
            result = ",".join(value)
        elif isinstance(value, list):
            result = json.dumps(value)
        elif value is None:
            # csv.writer will convert None values to an empty element
            result = None
        else:
            raise TypeError(
                "Parsed type {} detected. Only date, numeric, string-types"
                " tuples of strings, and 'None' are supported".format(type(value))
            )
        return result

    @staticmethod
    def decode_value(value, value_type):
        # The encoder used to encode None values as the string "None", which
        # isn't standard for CSV files.
        # The encoder now encodes None values as an empty element to be
        # cross-application safe.
        # The python CSV reader sets the value of empty CSV elements to the
        # empty string
        if value != "":
            if value_type == datetime:
                # convert all dates to UTC
                result = to_datetime(int(value))
            elif value_type == timedelta:
                result = timedelta(seconds=float(value))
            elif value_type == date:
                result = date.fromisoformat(value)
            elif value_type == bool:
                result = bool(int(value))
            elif value_type == int:
                result = int(value)
            elif value_type == float:
                result = float(value)
            elif value_type == Decimal:
                result = Decimal(value)
            elif issubclass(value_type, str):
                result = str(value)
            elif value_type == tuple:
                result = tuple(value.split(","))
            elif value_type == list:
                result = json.loads(value)
            else:
                raise TypeError(
                    "Unable to decode '{}'. Only date, numeric, string-types"
                    " tuples of strings, and 'None' are supported".format(value_type)
                )
        else:
            result = None

        return result

    def close(self):
        self.string_buffer.seek(0)
        del self.writer
        del self.header

        return self.string_buffer
