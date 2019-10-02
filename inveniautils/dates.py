import calendar
import collections
import regex
import pytz

from datetime import datetime, timedelta
from inveniautils.mathutil import RoundingMode, round_to
from dateutil.parser import parse as dateutil_parse
from pytz import utc


# Special is_dst parameter which tells pytz localize to explicitly guess
# the timezone offset during ambigious or non-existent times.
GUESS_DST = object()


def localize(dt, tz, is_dst=None):
    if dt.tzinfo is not None:
        raise ValueError("Not naive datetime (tzinfo is already set)")

    if hasattr(tz, 'localize'):
        # By default if you don't specify the is_dst flag the localize
        # method will guess the timezone offset during ambiguous or
        # non-existent times.
        if is_dst is GUESS_DST:
            localized = tz.localize(dt)
        else:
            # Note that when dealing with non-existent times and the is_dst
            # flag is a boolean will cause localize to not throw an exception.
            try:
                localized = tz.localize(dt, is_dst=None)
            except pytz.exceptions.AmbiguousTimeError:
                if is_dst is not None:
                    localized = tz.localize(dt, is_dst=is_dst)
                else:
                    raise
    else:
        localized = dt.replace(tzinfo=tz)

    return localized


def localize_period_ending(dt, tz, period, is_dst=None):
    dt -= period  # Period-ending to period-beginning.
    dt = localize(dt, tz, is_dst)
    dt += period  # Period-beginning to period-ending.
    return dt


def localize_hour_ending(dt, tz, is_dst=None):
    period = timedelta(hours=1)
    return localize_period_ending(dt, tz, period, is_dst)


#   Issue #228: Create test case using this as a test:
#   tz = pytz.timezone('America/New_York')
#   today = tz.localize(datetime(2014, 3, 10))
#   today.replace(day=7)  # Set to 7th of month. Note should be EST
#   today.replace(day=7).astimezone(tz)  # No longer the 7th but EST
#   tz.localize(datetime(2014, 3, 7))    # We want and expect this
def relocalize(dt, is_dst=None):
    return localize(dt.replace(tzinfo=None), dt.tzinfo, is_dst)


#  Issue #228: Create test cases using these:
#  dt = localize(datetime(2014, 11, 2), pacific)
#  (dt + timedelta(hours=24)).astimezone(dt.tzinfo) # Incorrect
#  (dt + timedelta(hours=24)).astimezone(pacific)   # Correct
#  dt.tzinfo.normalize(dt + timedelta(hours=24))    # Correct
#
#  dt = localize(datetime(2014, 3, 9), pacific)
#  (dt + timedelta(hours=24)).astimezone(dt.tzinfo) # Incorrect
#  (dt + timedelta(hours=24)).astimezone(pacific)   # Correct
#  dt.tzinfo.normalize(dt + timedelta(hours=24))    # Correct
def normalize(dt):
    if dt.tzinfo is not None:
        tz = dt.tzinfo
    else:
        raise ValueError("Naive datetime cannot be normalized")

    if hasattr(tz, 'normalize'):
        normalized = tz.normalize(dt)
    else:
        normalized = dt.astimezone(tz)

    return normalized


# Note: pytz timezones in spring are not the skipped datetime while
# dateutil.tz.gettz does.
def timezone_transitions(timezone, year=None):
    # First year DST was ever used. Note: This is only needed since
    # some timezones include datetime(1, 1, 1) as a transition.
    first_implemented_year = 1916

    if hasattr(timezone, '_utc_transition_times'):
        transitions = (
            localize(dt, utc).astimezone(timezone)
            for dt in timezone._utc_transition_times
            if year is None and dt.year >= first_implemented_year or
            year is not None and dt.year == year
        )

    elif hasattr(timezone, '_trans_list'):
        transitions = (
            datetime.fromtimestamp(t, utc).replace(tzinfo=timezone)
            for t in timezone._trans_list
        )

        if year is not None:
            transitions = (
                dt for dt in transitions
                if dt.year == year
            )

    else:
        raise TypeError("Timezone does not contain any transition information")

    return transitions


def split(dates, pivot):
    """
    Separates the given dates into two groups. The two groups will
    contain only dates before and after the pivot point respectively.
    """
    from .datetime_range import DatetimeRange, Bound

    if not isinstance(dates, collections.Iterable):
        dates = [dates]

    before = []
    after = []

    for d in dates:
        if isinstance(d, DatetimeRange):
            if d < pivot:
                before.append(d)
            elif d > pivot:
                after.append(d)
            else:
                before.append(
                    DatetimeRange(
                        d.start, pivot, (d.start_bound, Bound.EXCLUSIVE),
                    )
                )
                after.append(
                    DatetimeRange(
                        pivot, d.end, (Bound.INCLUSIVE, d.end_bound),
                    )
                )

        else:
            if d < pivot:
                before.append(d)
            else:
                after.append(d)

    return before, after


def timezone(name, offset):
    if name is not None:
        return pytz.timezone(name)
    else:
        return pytz.FixedOffset(offset // 60)  # dateutils gives offset in secs


def parse(timestr, tzinfos=timezone, **kwargs):
    """This replaces dateutil's timezones with pytz's in parse.

    One unfortunate side-effect is that this version of parse does
    not accept any additional positional arguments.
    """
    return dateutil_parse(timestr, tzinfos=tzinfos, **kwargs)


def format_to_regex(format):
    # Note: We require the "regex" module here since we are using
    # possessive qualifiers. eg. {m,n}+
    # Note: We could make the regex's filter out things like 99
    # months but this would make the behaviours harder to test.
    translation = {
        'Y': {
            'group': 'year',
            'expr': r'\d{4}',
            'digits': [4],
        },
        'm': {
            'group': 'month',
            'expr': r'\d{1,2}+',
            'digits': [1, 2],
        },
        'd': {
            'group': 'day',
            'expr': r'\d{1,2}+',
            'digits': [1, 2],
        },
        'H': {
            'group': 'hour',
            'expr': r'\d{1,2}+',
            'digits': [1, 2],
        },
        'M': {
            'group': 'minute',
            'expr': r'\d{1,2}+',
            'digits': [1, 2],
        },
        'S': {
            'group': 'second',
            'expr': r'\d{1,2}+',
            'digits': [1, 2],
        },
        'f': {
            'group': 'microsecond',
            'expr': r'\d{1,6}+',
            'digits': range(1, 7),
        },
    }
    directive = regex.compile(r'\%(?P<digits>\d+)?(?P<key>[YmdHMSf])')

    result = format
    for m in regex.finditer(directive, format):
        key = m.group('key')
        group_name = translation[key]['group']

        # Allow the user to explicitly set the expected number of digits.
        if m.group('digits'):
            digits = int(m.group('digits'))

            if digits in translation[key]['digits']:
                replacement = r'\d{{{}}}'.format(digits)
            else:
                raise ValueError(
                    "Number of digits {} is unsupported by directive %{}.".
                    format(digits, key)
                )
        else:
            replacement = translation[key]['expr']

        result = result.replace(
            m.group(0),
            "(?P<{}>{})".format(group_name, replacement),
        )

    return regex.compile(result)


def datetime_extract(string, regexp):
    m = regex.search(regexp, string)

    if not m:
        raise ValueError(
            "Unable to extract datetime from '{}'".format(string)
        )

    d = m.groupdict()
    if isinstance(d.get('microsecond'), str):
        d['microsecond'] += '0' * (6 - len(d['microsecond']))

    values = {k: int(v) for k, v in d.items() if v is not None}
    return datetime(**values)


def round_datetime(dt=None, interval=timedelta(0), floor=False, ceil=False):
    """
    Round a datetime object to any timedelta/relativedelta.
    dt : datetime.datetime object with or without tzinfo. Defaults to now().
    interval : datetime.timedelta object to round towards.

    Note: This function will work over DST transitions on period
    beginning datetimes even if the datetime isn't relocalized.
    """
    # Note: Make sure that to matter what timezone is passed in that
    # dates are rounded to the local timezone and not UTC.

    if dt is None:
        dt = datetime.now()

    tz = dt.tzinfo

    if hasattr(interval, 'total_seconds'):
        interval = interval.total_seconds()

        # Abort early if there is nothing to round to.
        if interval == 0:
            return dt

        timestamp = calendar.timegm(dt.utctimetuple())  # Timestamp in UTC

        # Determine the timezone's offset from UTC.
        if tz is not None:
            # Corrects badly created datetimes.
            # Alternatively convert to a fixed timezone then back:
            # dt = dt.astimezone(utc).astimezone(tz)
            if hasattr(tz, 'normalize'):
                dt = tz.normalize(dt)

            offset = dt.utcoffset().total_seconds()
        else:
            offset = 0  # Apply no offset when tz-naive

        # Calculate the local timestamp's deviation from interval. We need to
        # perform the conversion with local timestamps to ensure that rounding
        # to the nearest day works correctly.
        remainder = (timestamp + offset) % interval

        # Floor the timestamp.
        timestamp = timestamp - remainder

        # Increase by interval when using ceil or needing to rounding up.
        if ceil and remainder > 0:
            timestamp = timestamp + interval
        elif not floor and not ceil and remainder >= interval / 2.0:
            timestamp = timestamp + interval

        # Timestamp is in UTC
        dt = datetime.fromtimestamp(timestamp, utc)

        # Rounded datetime is in UTC but needs to be returned in the
        # same timezone that it started with.
        if tz is not None:
            dt = dt.astimezone(tz)

            # Correct for rounding across different timezone offsets.
            # We only want to do this if rounding to more than an hour
            if interval > timedelta(hours=1).total_seconds():
                rounded_offset = dt.utcoffset().total_seconds()
                if rounded_offset != offset:
                    dt += timedelta(seconds=offset - rounded_offset)
        else:
            dt = dt.replace(tzinfo=None)

    else:
        # Use the UNIX epoch as a base.
        base = datetime.utcfromtimestamp(0)

        if tz is not None:
            base = localize(base, tz)

        # Abort early if there is nothing to round to. Note: Without
        # this check an infinite loop will occur below since the
        # addition/subtraction of theinterval results in no change.
        if base == base + interval:
            return dt

        # Find the floor and ceiling where floored <= dt < ceiled
        if base <= dt:
            ceiled = base
            while ceiled <= dt:
                floored = ceiled
                ceiled = relocalize(ceiled + interval)
        else:
            floored = base
            while floored > dt:
                ceiled = floored
                floored = relocalize(floored - interval)

        # Note: Use the floor if dt == floored.
        remainder = dt - floored
        if floor or remainder == timedelta(0):
            dt = floored
        elif ceil:
            dt = ceiled
        else:
            gap = ceiled - dt
            dt = floored if remainder < gap else ceiled

    return dt


def round_timedelta(delta, interval, mode=RoundingMode.NEAREST_TIES_FROM_ZERO):
    """
    Round a timedelta to the provided interval.

    delta: timedelta object to round
    interval : timedelta object to round toward
    mode: modifies the behaviour of how the timedelta is rounded
    """
    return timedelta(
        seconds=round_to(
            delta.total_seconds(),
            interval.total_seconds(),
            mode,
        )
    )


def estimate_latest_release(
    now, publish_interval, publish_offset, datafeed_runtime=timedelta(0)
):
    """
    Estimates the latest release date given the current time and the typical
    publication interval and offset. Useful in estimating the avaialble
    content end at a specific time.
    """
    return relocalize(
        round_datetime(
            now - publish_offset - datafeed_runtime,
            publish_interval,
            floor=True,
        ) + publish_offset
    )


def estimate_content_end(release_date, content_interval, content_offset):
    """
    Estimates the content end given the release date and the content interval
    and offset.
    """
    return relocalize(
        round_datetime(
            release_date,
            content_interval,
            floor=True,
        ) + content_offset
    )


def estimate_latest(now, est, datafeed_runtime=timedelta(0)):
    """
    Estimates both the latest release date and latest content end at once.
    """
    publish_interval, publish_offset, content_interval, content_offset = est
    latest_release_date = estimate_latest_release(
        now, publish_interval, publish_offset, datafeed_runtime
    )
    latest_content_end = estimate_content_end(
        latest_release_date, content_interval, content_offset
    )
    return latest_release_date, latest_content_end


def contains(dates, date):
    """Check if date is in dates."""
    from .datetime_range import DatetimeRange

    if dates is None:
        dates = []

    if not isinstance(dates, collections.Iterable):
        dates = [dates]

    for d in dates:
        if isinstance(d, DatetimeRange):
            if d.contains(date):
                return True
        else:
            if date == d:
                return True

    return False
