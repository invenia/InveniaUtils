from __future__ import annotations

import re
from typing import Any, Iterator, Optional, Tuple, Union
import warnings

from collections.abc import Iterable
from datetime import datetime, timedelta, tzinfo
from enum import IntEnum
from functools import partial
from functools import cmp_to_key

from inveniautils.compat import cmp
from inveniautils.dates import GUESS_DST, normalize, relocalize, round_datetime, utc

from dateutil.parser import parse as datetime_parser
from dateutil.relativedelta import relativedelta


MATH_RANGE = re.compile(
    r"""
    ^\s*
    (?P<inclusive_start>[\(\[])
    \s*
    (?P<start_date>.+?)
    \s*,\s*
    (?P<end_date>.+?)
    \s*
    (?P<inclusive_end>[\)\]])
    \s*$
""",
    re.VERBOSE,
)


SIMPLE_RANGE = re.compile(
    r"""
    ^\s*
    (?P<start_date>.+?)
    \s+to\s+
    (?P<end_date>.+?)
    \s*$
""",
    re.VERBOSE,
)

# Note: Should make an actual infinite datetime.
POS_INF_DATETIME = datetime.max
POS_INF_DATETIME_TZ = datetime.max.replace(tzinfo=utc)


def is_positive_delta(delta: Union[timedelta, relativedelta]) -> bool:
    fields = [
        "days",
        "hours",
        "leapdays",
        "microseconds",
        "minutes",
        "months",
        "seconds",
        "years",
    ]

    if isinstance(delta, relativedelta):
        for field in fields:
            if getattr(delta, field) > 0:
                return True
    elif isinstance(delta, timedelta):
        if delta > timedelta(0):
            return True

    return False


def is_zero_delta(delta: Union[timedelta, relativedelta]) -> bool:
    fields = [
        "days",
        "hours",
        "leapdays",
        "microseconds",
        "minutes",
        "months",
        "seconds",
        "years",
    ]

    if isinstance(delta, relativedelta):
        for field in fields:
            if getattr(delta, field) != 0:
                return False
    elif isinstance(delta, timedelta):
        if delta != timedelta(0):
            return False

    return True


def is_infinite_datetime(dt: datetime) -> bool:
    if dt.tzinfo is not None:
        return dt == POS_INF_DATETIME_TZ
    else:
        return dt == POS_INF_DATETIME


def pos_infinite_datetime(tz_aware: bool) -> datetime:
    if tz_aware:
        return POS_INF_DATETIME_TZ
    else:
        return POS_INF_DATETIME


def start_before_key(dtr: DatetimeRange) -> Tuple[datetime, bool]:
    return (dtr.start, dtr.start_bound == Bound.EXCLUSIVE)


def sort_key(dtr: DatetimeRange) -> Tuple[datetime, bool, datetime, bool]:
    # start and end bounds are inverted because an inclusive start
    # starts first and an exclusive end ends first.
    return (
        dtr.start,
        dtr.start_bound == Bound.EXCLUSIVE,
        dtr.end,
        dtr.end_bound == Bound.INCLUSIVE,
    )


def period_ending_as_range(dt: datetime, period: timedelta) -> DatetimeRange:
    """
    Converts a implicit period-ending datetime and converts it into an
    appropriate datetime range. May not work as expected if you want
    units such as "a day".
    """
    return DatetimeRange(normalize(dt - period), dt, (Bound.INCLUSIVE, Bound.EXCLUSIVE))


def period_beginning_as_range(dt: datetime, period: timedelta) -> DatetimeRange:
    """
    Converts a implicit period-beginning datetime and converts it into an
    appropriate datetime range. May not work as expected if you want
    units such as "a day".
    """
    return DatetimeRange(dt, normalize(dt + period), (Bound.INCLUSIVE, Bound.EXCLUSIVE))


# We're deprecating this because cmp is gone in Python3 and also because
# the non-datetime range option here is a reach. Also, that type should
# technically be Tuple[DatetimeRange, Any...], but mypy doesn't
# understand that.
def cmp_ranges(
    a: Union[DatetimeRange, Tuple[Any, ...]], b: Union[DatetimeRange, Tuple[Any, ...]]
) -> int:
    """
    Compare two DatetimeRanges (or tuples where the first element is a
    DatetimeRange).

    a < b if a starts before b or they start at the same time and a ends
    first.
    """
    warnings.warn(
        (
            "This method will be removed in inveniautils 0.4.0. "
            "Use key=sort_key when sorting."
        ),
        DeprecationWarning,
        stacklevel=2,
    )

    if isinstance(a, tuple) and isinstance(b, tuple):
        # The sort key for outages is a tuple starting with
        # target_range rather than just the range itself.
        if isinstance(a[0], DatetimeRange) and isinstance(b[0], DatetimeRange):
            result = cmp_ranges(a[0], b[0])

            if result != 0:
                return result
            elif a[1:] < b[1:]:
                return -1
            elif a[1:] == b[1:]:
                return 0
            else:
                return 1
        else:
            raise TypeError(
                "First element of an operand was not a date"
                " range:\na[0]={}\nb[0]={}".format(a[0], b[0])
            )
    elif isinstance(a, DatetimeRange) and isinstance(b, DatetimeRange):
        if a.starts_before(b) or not a.starts_after(b) and a.ends_before(b):
            return -1
        elif a.starts_after(b) or a.ends_after(b):
            return 1
        else:
            return 0
    else:
        raise TypeError(
            "Operands must both be date ranges or tuples with"
            f" date ranges as their first element:\na={a}\nb={b}"
        )


class Bound(IntEnum):
    EXCLUSIVE = 0
    INCLUSIVE = 1
    OPEN = 0
    CLOSED = 1

    @classmethod
    def valid(cls, value: int) -> bool:
        warnings.warn(
            (
                "This method will be removed in inveniautils 0.4.0 "
                "and Bound will be converted from an IntEnum into an Enum. "
                "Bounds can be directly built using Bound(value)."
            ),
            DeprecationWarning,
            stacklevel=2,
        )

        return value in (Bound.EXCLUSIVE, Bound.INCLUSIVE)


class DatetimeRange:
    def __init__(
        self,
        start: datetime,
        end: Optional[datetime],
        bounds: Union[Bound, Tuple[Bound, Bound]] = Bound.INCLUSIVE,
    ):
        self._start = start

        if end is None:
            self._infinite_end = True
            self._end = pos_infinite_datetime(self._start.tzinfo is not None)
        else:
            self._end = end
            self._infinite_end = is_infinite_datetime(end)

        # Both start and end should either be offset-aware or
        # offset-naive.
        start_tz = self._start.tzinfo
        end_tz = self._end.tzinfo
        if (
            start_tz is None
            and end_tz is not None
            or start_tz is not None
            and end_tz is None
        ):
            raise ValueError(
                "Both start and end date must be either offset-naive or "
                "offset-aware datetimes"
            )

        # Expecting start to be before end.
        if self._start > self._end:
            raise ValueError("Start of range must not be greater than end of range.")

        # Handle assignment of bounds as one value.
        if isinstance(bounds, Bound):
            bounds = (bounds, bounds)

        if isinstance(bounds, tuple) and len(bounds) == 2:
            self._include_start = bounds[0] == Bound.INCLUSIVE
            self._include_end = bounds[1] == Bound.INCLUSIVE
        else:
            raise ValueError("Bounds expected to be a two element tuple.")

        # Unbounded range should not include that end point.
        if self._infinite_end:
            self._include_end = False

    @classmethod
    def fromstring(cls, range_str: str) -> DatetimeRange:
        # Base ensures that "2012 to 2013" is "2012/1/1 to 2013/1/1".
        base = datetime(datetime.now().year, 1, 1)

        # Attempt various regular expressions until one matches.
        component = {}
        for regex in [MATH_RANGE, SIMPLE_RANGE]:
            match = regex.search(range_str)

            if match:
                component = match.groupdict()
                break

        if component:
            try:
                start_date = datetime_parser(component["start_date"], default=base)
            except TypeError:
                raise ValueError(
                    "Unable to parse start date: {}".format(component["start_date"])
                )

            try:
                if component["end_date"] == "Inf":
                    end_date = None
                else:
                    end_date = datetime_parser(component["end_date"], default=base)
            except TypeError:
                raise ValueError(
                    "Unable to parse end date: {}".format(component["end_date"])
                )

            if (
                "inclusive_start" in component and component["inclusive_start"] == "("
            ):  # noqa: E501
                start_bound = Bound.EXCLUSIVE
            else:
                start_bound = Bound.INCLUSIVE

            if (
                "inclusive_end" in component and component["inclusive_end"] == ")"
            ):  # noqa: E501
                end_bound = Bound.EXCLUSIVE
            else:
                end_bound = Bound.INCLUSIVE
        else:
            raise ValueError('Invalid datetime range "{}"'.format(range_str))

        return cls(start_date, end_date, bounds=(start_bound, end_bound))

    def copy(self):
        return DatetimeRange(self._start, self._end, (self.start_bound, self.end_bound))

    @classmethod
    def containing(
        cls,
        dates: Union[datetime, DatetimeRange, Iterable[Union[datetime, DatetimeRange]]],
    ) -> DatetimeRange:
        """
        Create a DatetimeRange that spans the length of one or more
        dates or DatetimeRanges
        """
        container = None
        if not isinstance(dates, Iterable):
            dates = [dates]

        for date in dates:
            if container:
                if isinstance(date, DatetimeRange):
                    if container.starts_after(date):
                        container.start = date.start
                        container.start_bound = date.start_bound

                    if container.ends_before(date):
                        container.end = date.end
                        container.end_bound = date.end_bound
                        container.end_infinite = date.end_infinite
                else:
                    if container.starts_after(date):
                        container.start = date
                        container.start_bound = Bound.INCLUSIVE

                    if container.ends_before(date):
                        container.end = date
                        container.end_bound = Bound.INCLUSIVE
            else:
                if isinstance(date, DatetimeRange):
                    container = date.copy()
                else:
                    container = cls(date, date)

        if container is None:
            raise ValueError("No dates supplied")

        return container

    @classmethod
    def effective_ranges(
        cls, effective_dates: Iterable[datetime]
    ) -> Iterator[DatetimeRange]:
        """
        Takes a complete set of effective datetimes and creates the
        ranges that they are effective for. Note that the given
        effective dates needs to a complete set since the last effective
        range will extend infinitely.

        effective_dates: iterable of datetimes objects. All datetimes
          need to be either timezone-aware or not.
        """
        effective_dates = sorted(effective_dates)

        infinite_date = datetime.max

        # Make infinite datetime timezone aware if datetimes are
        # timezone aware.
        if effective_dates and effective_dates[0].tzinfo:
            infinite_date = infinite_date.replace(tzinfo=utc)

        effective_start, effective_until = None, None
        for effective_date in effective_dates + [infinite_date]:
            effective_until = effective_date

            if effective_start is not None and effective_until is not None:
                yield cls(
                    effective_start, effective_until, (Bound.INCLUSIVE, Bound.EXCLUSIVE)
                )

            effective_start = effective_until

    @classmethod
    def reduce(cls, ranges: Iterable[DatetimeRange]) -> Iterator[DatetimeRange]:
        """
        Combines a iterable of ranges into an equivalent set of ranges
        with containing no overlaps ranges.

        ranges: iterable of date range objects.
        """
        # Order ranges in order to make reduction easier.
        ranges = sorted(
            ranges,
            key=cmp_to_key(  # type: ignore
                lambda x, y: (  # type: ignore
                    cmp(x.start, y.start)  # type: ignore
                    or cmp(y.start_included, x.start_included)  # type: ignore
                    or cmp(y.end, x.end)  # type: ignore
                    or cmp(y.end_included, x.end_included)  # type: ignore
                )
            ),
        )

        expanded = None
        for dtr in ranges:
            if expanded is None:
                expanded = dtr.copy()
            elif expanded.before_touching(dtr) or expanded.before_overlaps(dtr):
                expanded.end = dtr.end
                expanded.end_included = dtr.end_included
            elif expanded.before_disjoint(dtr):
                yield expanded
                expanded = dtr.copy()

        if expanded is not None:
            yield expanded

    def aligned(self, period: datetime, expand: bool = True):
        floor_datetime = partial(round_datetime, floor=True)
        ceil_datetime = partial(round_datetime, ceil=True)

        adjust_start = floor_datetime if expand else ceil_datetime
        adjust_end = ceil_datetime if expand else floor_datetime

        start = adjust_start(self._start, period)
        if not self._infinite_end:
            end = adjust_end(self._end, period)
        else:
            end = None

        return DatetimeRange(start, end, (self.start_bound, self.end_bound))

    def astimezone(self, tz: tzinfo) -> DatetimeRange:
        if not self.tz_aware:
            raise ValueError("astimezone() cannot be applied to a naive DatetimeRange")

        return DatetimeRange(
            self._start.astimezone(tz),
            self._end.astimezone(tz),
            (self.start_bound, self.end_bound),
        )

    @property
    def start(self) -> datetime:
        return self._start

    @start.setter
    def start(self, value: datetime):
        tz_aware = value.tzinfo is not None

        if self.tz_aware == tz_aware and value <= self._end:
            self._start = value
        elif self.tz_aware != tz_aware and not self.tz_aware:
            raise ValueError(
                "DatetimeRange is currently timezone naive and requires a "
                "offset-naive end datetime"
            )
        elif self.tz_aware != tz_aware and self.tz_aware:
            raise ValueError(
                "DatetimeRange is currently timezone aware and requires a "
                "offset-aware end datetime"
            )
        else:
            raise ValueError("Start datetime cannot be greater than end datetime")

    @property
    def end(self) -> datetime:
        return self._end

    @end.setter
    def end(self, value: datetime):
        # Convert None into Inf
        if value is None:
            value = pos_infinite_datetime(self.tz_aware)

        tz_aware = value.tzinfo is not None

        if self.tz_aware == tz_aware and value >= self._start:
            self._end = value
            self.end_infinite = is_infinite_datetime(value)
        elif self.tz_aware != tz_aware and not self.tz_aware:
            raise ValueError(
                "DatetimeRange is currently timezone naive and requires a "
                "offset-naive end datetime"
            )
        elif self.tz_aware != tz_aware and self.tz_aware:
            raise ValueError(
                "DatetimeRange is currently timezone aware and requires a "
                "offset-aware end datetime"
            )
        else:
            raise ValueError("End datetime cannot be less than start datetime")

    @property
    def start_included(self) -> bool:
        return self._include_start

    @start_included.setter
    def start_included(self, value: bool):
        self._include_start = value

    @property
    def end_included(self) -> bool:
        return self._include_end

    @end_included.setter
    def end_included(self, value: bool):
        if self._infinite_end:
            raise ValueError(
                "Unable to set end to included on a range with an " "infinite range"
            )

        self._include_end = value

    @property
    def start_bound(self) -> Bound:
        if self._include_start:
            return Bound.INCLUSIVE
        else:
            return Bound.EXCLUSIVE

    @start_bound.setter
    def start_bound(self, value: Bound):
        if Bound.valid(value):
            self._include_start = value == Bound.INCLUSIVE
        else:
            raise ValueError("Invalid starting bound. Use Bound class instead.")

    @property
    def end_bound(self) -> Bound:
        if self._include_end:
            return Bound.INCLUSIVE
        else:
            return Bound.EXCLUSIVE

    @end_bound.setter
    def end_bound(self, value: Bound):
        if self._infinite_end:
            raise ValueError(
                "Unable to set end bound on a range with an " "infinite range"
            )

        if Bound.valid(value):
            self._include_end = value == Bound.INCLUSIVE
        else:
            raise ValueError("Invalid ending bound. Use Bound class instead.")

    @property
    def end_infinite(self) -> bool:
        return self._infinite_end

    @end_infinite.setter
    def end_infinite(self, value: bool):
        self._infinite_end = value

        if value:
            self._end = pos_infinite_datetime(self._end.tzinfo is not None)
            self._include_end = False

    @property
    def bounds(self) -> Tuple[Bound, Bound]:
        return (self.start_bound, self.end_bound)

    @property
    def infinite_endpoints(self) -> bool:
        return self._infinite_end

    @property
    def tz_aware(self) -> bool:
        return self._start.tzinfo is not None

    @tz_aware.setter
    def tz_aware(self, value: bool):
        if not isinstance(value, bool):
            raise ValueError("tz_aware must of type bool")

        if value:
            if self._start.tzinfo is None:
                self._start = self._start.replace(tzinfo=utc)
            if self._end.tzinfo is None:
                self._end = self._end.replace(tzinfo=utc)
        else:
            if self._start.tzinfo is not None:
                self._start = self._start.astimezone(utc)
                self._start = self._start.replace(tzinfo=None)
            if self._end.tzinfo is not None:
                self._end = self._end.astimezone(utc)
                self._end = self._end.replace(tzinfo=None)

    def before_disjoint(self, date: Union[datetime, DatetimeRange]) -> bool:
        """
        Compare a datetime range (A) to a datetime range or datetime (B)
        to see if the A occurs before B with no overlap.
        """
        if isinstance(date, DatetimeRange):
            return self.end < date.start or (
                (not self.end_included or not date.start_included)
                and self.end == date.start
            )
        else:
            return self.end < date or (not self.end_included and self.end == date)

    def after_disjoint(self, date: Union[datetime, DatetimeRange]) -> bool:
        """
        Compare a datetime range (A) to a datetime range or datetime (B)
        to see if the A occurs after B with no overlap.
        """
        if isinstance(date, DatetimeRange):
            return self.start > date.end or (
                (not self.start_included or not date.end_included)
                and self.start == date.end
            )
        else:
            return self.start > date or (not self.start_included and self.start == date)

    def before_overlaps(self, dtr: DatetimeRange) -> bool:
        """
        Compare two datetime ranges (A, B) to see if the A starts
        before the start of the B and the A ends within B.
        """
        starts_before = self.start < dtr.start or (
            self.start_included and not dtr.start_included and self.start == dtr.start
        )

        ends_before_or_equal = self.end < dtr.end or (
            (not self.end_included or dtr.end_included) and self.end == dtr.end
        )

        overlap = self.end > dtr.start or (
            self.end_included and dtr.start_included and self.end == dtr.start
        )

        return starts_before and ends_before_or_equal and overlap

    def after_overlaps(self, dtr: DatetimeRange) -> bool:
        return dtr.before_overlaps(self)

    def overlaps(self, dtr: DatetimeRange) -> bool:
        """
        Compare two datetime ranges (A, B) to see if the A and B overlap
        in anyway.
        """
        return (
            self.start < dtr.end
            and self.end > dtr.start
            or dtr.start < self.end
            and dtr.end > self.start
            or self.end_included
            and dtr.start_included
            and self.end == dtr.start
            or dtr.end_included
            and self.start_included
            and dtr.end == self.start
        )

    def before_touching(self, dtr: DatetimeRange) -> bool:
        return (self.end_included or dtr.start_included) and self.end == dtr.start

    def after_touching(self, dtr: DatetimeRange) -> bool:
        return dtr.before_touching(self)

    def starts_before(self, date: Union[datetime, DatetimeRange]) -> bool:
        """
        Compare two datetime ranges (A, B) to see if the start A
        preceeds the start of B.
        """
        if isinstance(date, DatetimeRange):
            return self.start < date.start or (
                self.start_included
                and not date.start_included
                and self.start == date.start
            )
        else:
            return self.start < date

    def starts_after(self, date: Union[datetime, DatetimeRange]) -> bool:
        """
        Compare two datetime ranges (A, B) to see if the start A
        proceeds the start of B.
        """
        if isinstance(date, DatetimeRange):
            return date.starts_before(self)
        else:
            return self.start > date or (not self.start_included and self.start == date)

    def ends_before(self, date: Union[datetime, DatetimeRange]) -> bool:
        """
        Compare two datetime ranges (A, B) to see if the end A
        preceeds the end of B.
        """
        if isinstance(date, DatetimeRange):
            return self.end < date.end or (
                not self.end_included and date.end_included and self.end == date.end
            )
        else:
            return self.end < date or (not self.end_included and self.end == date)

    def ends_after(self, date: Union[datetime, DatetimeRange]) -> bool:
        """
        Compare two datetime ranges (A, B) to see if the end A
        proceeds the end of B.
        """
        if isinstance(date, DatetimeRange):
            return date.ends_before(self)
        else:
            return self.end > date

    def contains(self, date: Union[datetime, DatetimeRange]) -> bool:
        if isinstance(date, DatetimeRange):
            return (
                date.start > self.start
                or date.start == self.start
                and (self.start_included or not date.start_included)
            ) and (
                date.end < self.end
                or date.end == self.end
                and (self.end_included or not date.end_included)
            )
        else:
            return (
                self._start < date < self._end
                or self._include_start
                and self._start == date
                or self._include_end
                and self._end == date
            )

    def __eq__(self, dtr: Any) -> bool:
        if not isinstance(dtr, DatetimeRange):
            return NotImplemented

        return (
            self.start == dtr.start
            and self.end == dtr.end
            and self.start_included == dtr.start_included
            and self.end_included == dtr.end_included
        )

    def __ne__(self, dtr: Any) -> bool:
        return not self.__eq__(dtr)

    def __lt__(self, date: Any) -> bool:
        if isinstance(date, DatetimeRange):
            return NotImplemented

        return self.end < date or (not self.end_included and self.end == date)

    def __gt__(self, date: Any) -> bool:
        if isinstance(date, DatetimeRange):
            return NotImplemented

        return self.start > date or (not self.start_included and self.start == date)

    def __contains__(self, date: Union[datetime, DatetimeRange]) -> bool:
        return self.contains(date)

    # We need this because otherwise python will use __len__
    def __bool__(self) -> bool:
        return True

    def __len__(self) -> int:
        return int(self.size().total_seconds())

    def __hash__(self) -> int:
        # Note: Probably could have a better hashing algorithm but this
        # functionally works.
        return hash((self.start, self.end, self.start_included, self.end_included))

    def size(self) -> timedelta:
        """
        Return a timedelta representing the length of the range.

        NOTE: Will raise a ValueError if the range is infinite
        """
        if self._infinite_end:
            raise ValueError("Datetime range has infinite size")

        return self.end - self.start

    def overlapping_range(self, dtr: DatetimeRange) -> DatetimeRange:
        if not self.overlaps(dtr):
            raise ValueError("Ranges do not overlap!")

        if self.start > dtr.start or (
            not self.start_included and self.start == dtr.start
        ):
            start = self.start
            start_bound = self.start_bound
        else:
            start = dtr.start
            start_bound = dtr.start_bound

        if self.end < dtr.end or (not self.end_included and self.end == dtr.end):
            end = self.end
            end_bound = self.end_bound
        else:
            end = dtr.end
            end_bound = dtr.end_bound

        return DatetimeRange(start, end, (start_bound, end_bound))

    def intersection(self, dtr: DatetimeRange) -> DatetimeRange:
        return self.overlapping_range(dtr)

    def dates(
        self, interval: timedelta, reverse: bool = False, tz: tzinfo = None
    ) -> Iterator[datetime]:
        """
        Generates a series of datetimes separated by the interval
        starting with the range start and ending on or before the range
        end.

        :param interval: period between yielded datetimes
        :param reverse: datetimes are yielded backwards and start with
            the end of the range and finish with the start of the range.
        """
        # Switch how we adjust the datetime after we add the interval.
        # Note: Using a variation on relocalize where ambigious
        # datetimes are resolved by guessing.
        # Note: Works best with pytz timezones.
        if self._infinite_end:
            raise ValueError("Unable to compute dates on an infinite range")

        is_relative = isinstance(interval, relativedelta)

        if self.tz_aware:
            if not is_relative and interval < timedelta(hours=2):
                adjust = normalize
            else:
                adjust = partial(relocalize, is_dst=GUESS_DST)
        else:
            adjust = lambda dt: dt

        if reverse:
            dt = self._end
            if not self._include_end:
                dt = adjust(dt - interval)
        else:
            dt = self._start
            if not self._include_start:
                dt = adjust(dt + interval)

        if not tz and self.tz_aware:
            tz = self._end.tzinfo if reverse else self._start.tzinfo

        if tz and self.tz_aware:
            dt = dt.astimezone(tz)
        elif tz and not self.tz_aware:
            raise ValueError("timezone cannot be applied to a naive DatetimeRange")

        if is_positive_delta(interval):
            if reverse:
                while dt > self._start:
                    yield dt
                    dt = adjust(dt - interval)

                if self._include_start and dt == self._start:
                    yield dt
            else:
                while dt < self._end:
                    yield dt
                    dt = adjust(dt + interval)

                if self._include_end and dt == self._end:
                    yield dt

        elif is_zero_delta(interval):
            yield dt
        else:
            raise ValueError("Interval only supports non-negative timedeltas.")

    def ranges(
        self,
        interval: timedelta,
        reverse: bool = False,
        tz: tzinfo = None,
        bounds: Tuple[Bound, Bound] = (Bound.INCLUSIVE, Bound.EXCLUSIVE),
    ):
        """
        Breaks up the range into a series of ranges which have a duration of
        size `interval`. The passed in `bounds` allows you to control the
        output bounds which are typically inclusive/exclusive
        (period-beginning) or exclusive/inclusive (period-ending).
        """

        # Modify the start/end bounds based upon the combination of
        # of the current datetime range and the new bounds.
        # Basically, when both bounds are exclusive we don't actually want to
        # skip that date as would normally occur when using dates.
        start_bound, end_bound = self.bounds
        output_start_bound, output_end_bound = bounds
        if start_bound == output_start_bound == Bound.EXCLUSIVE:
            start_bound = Bound.INCLUSIVE
        if end_bound == output_end_bound == Bound.EXCLUSIVE:
            end_bound = Bound.INCLUSIVE

        iterator = DatetimeRange(self.start, self.end, (start_bound, end_bound)).dates(
            interval, reverse, tz
        )

        last_dt, dt = next(iterator), None

        # Fun-fact: We're not 100% sure that this kind of range should exist
        if is_zero_delta(interval):
            yield DatetimeRange(last_dt, last_dt, bounds)
        else:
            for dt in iterator:
                yield DatetimeRange(last_dt, dt, bounds)
                last_dt = dt

    def __repr__(self) -> str:
        start_bound = "[" if self._include_start else "("
        end_bound = "]" if self._include_end else ")"

        start = self._start
        end = self._end if not self._infinite_end else "Inf"

        return "{}{}, {}{}".format(start_bound, start, end, end_bound)
