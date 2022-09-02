import calendar
from datetime import datetime

from inveniautils.dates import utc

invalid_timestamp = 2**63 - 1


def from_datetime(date: datetime) -> int:
    """
    Converts a datetime object to a UTC timestamp

    Args:
        date: A non-naive datetime

    Returns:
        A UTC timestamp integer
    """
    if date.tzinfo is None:
        raise TypeError("Expected a non-naive datetime (tzinfo is not set)")

    return calendar.timegm(date.utctimetuple())


# The timestamp that will be returned when datetime.max is sent to
# from_datetime().
# This timestamp should equal 253402300799
MAX_TIMESTAMP = from_datetime(datetime.max.replace(tzinfo=utc))


def to_datetime(timestamp: int) -> datetime:
    """
    Converts a UTC timestamp to a datetime

    Args:
        timestamp: A UTC timestamp

    Returns:
        A UTC datetime
    """

    # Note: datetime.max returns the datetime:
    #     datetime.datetime(9999, 12, 31, 23, 59, 59, 999999)
    #
    # When datetime.max is converted to a timestamp, the microseconds are lost
    # This is a workaround so that the following expression is True:
    #     dt = datetime.max.replace(tzinfo=utc)
    #     dt == to_datetime(from_datetime(dt))
    if timestamp == MAX_TIMESTAMP:
        dt = datetime.max.replace(tzinfo=utc)
    else:
        dt = datetime.fromtimestamp(timestamp, utc)

    return dt
