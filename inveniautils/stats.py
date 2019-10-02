from datetime import timedelta

from inveniautils.dates import round_datetime, round_timedelta
from inveniautils.datetime_range import DatetimeRange, start_before_key
from inveniautils.mathutil import RoundingMode


def instance_analysis(target_dates):
    smallest = largest = None
    steps = {}
    last_target_date = None
    for target_date in sorted(target_dates):
        if smallest is None or target_date < smallest:
            smallest = target_date
        if largest is None or target_date > largest:
            largest = target_date
        if last_target_date is not None:
            step = target_date - last_target_date
            if step not in steps:
                steps[step] = 0
            steps[step] += 1
        last_target_date = target_date

    best_step = None
    best_count = 0
    min_count = 0
    for step, count in steps.items():
        if count > best_count and count > min_count:
            best_step = step
            best_count = count
        elif best_count == count:
            min_count = count
            best_step = None

    if best_step is None and smallest == largest:
        best_step = timedelta(0)

    return smallest, best_step, largest


def range_analysis(ranges):
    empty = object()
    smallest = largest = empty
    steps = {}
    for dtr in sorted(ranges, key=start_before_key):
        if smallest is empty or (smallest and dtr.starts_before(smallest)):
            smallest = dtr.start
        if largest is empty or (largest and dtr.ends_after(largest)):
            largest = dtr.end if not dtr.end_infinite else None

        step = dtr.end - dtr.start if not dtr.infinite_endpoints else None
        if step not in steps:
            steps[step] = 0
        steps[step] += 1

    if smallest is empty:
        smallest = None
    if largest is empty:
        largest = None

    best_step = None
    best_count = 0
    min_count = 0
    for step, count in steps.items():
        if count > best_count and count > min_count:
            best_step = step
            best_count = count
        elif best_count == count:
            min_count = count
            best_step = None

    if best_step is None and smallest == largest:
        best_step = timedelta(0)

    return smallest, best_step, largest


def range_pair_analysis(pairs):
    return range_analysis(DatetimeRange(s, e) for s, e in pairs)


def best_delta(sample, interval=timedelta(0), tolerance=None):
    """
    Determine the timedelta that occurs the most frequently.

    sample: an iterable of timedeltas
    interval: the bucket size
    tolerance: allow using a less frequent delta if it occurs within X% of the
      most frequent delta
    """
    # Count the number of timedeltas that are within the same interval.
    interval = abs(interval)
    count = {}
    for delta in sample:
        if interval != timedelta(0):
            delta = round_timedelta(delta, interval, RoundingMode.FROM_ZERO)

        if delta not in count:
            count[delta] = 0
        count[delta] += 1

    # Determine the most frequently occurring delta.
    best_delta = None
    for delta, num in count.items():
        if best_delta is None or count[best_delta] < num:
            best_delta = delta

    # Prefer smaller deltas (towards zero) when the count isn't substantially
    # different. Note: Python 3 division.
    delta = best_delta
    if best_delta is not None and tolerance is not None and interval != timedelta(0):  # noqa: E501
        if best_delta < timedelta(0):
            while count.get(delta + interval, 0) / count[best_delta] >= tolerance:  # noqa: E501
                delta += interval
        else:
            while count.get(delta - interval, 0) / count[best_delta] >= tolerance:  # noqa: E501
                delta -= interval

    return delta


def compute_interval(datetimes, tolerance):
    """
    Determine the typical duration between a series of date times.
    """
    deltas = []
    prev_dt = None
    for dt in sorted(dt for dt in datetimes if dt is not None):
        if prev_dt is not None:
            delta = round_timedelta(dt - prev_dt, tolerance)
            if delta != timedelta(0):
                deltas.append(delta)
        prev_dt = dt

    return best_delta(deltas, tolerance)


def compute_offset(datetimes, interval, tolerance):
    """
    Determine the typical offset between a series of date times given their
    interval.
    """
    deltas = []
    for dt in datetimes:
        if dt is not None:
            # Each datetime needs to be in the correct timezone
            dt_floored = round_datetime(dt, interval, floor=True)
            deltas.append(round_timedelta(dt - dt_floored, tolerance))

    return best_delta(deltas, tolerance)


def compute_content_offset(
    release_dates, content_end_dates, release_interval, tolerance
):
    """
    Determine the typical content offset given a series of release dates,
    content end dates, and the release interval.
    """
    deltas = []
    for release_date, content_end in zip(release_dates, content_end_dates):
        if release_date is not None and content_end is not None:
            floored_release_date = round_datetime(
                release_date, release_interval, floor=True
            )
            deltas.append(content_end - floored_release_date)

    return best_delta(deltas, tolerance)


def release_estimations(release_dates, content_end_dates, tolerance):
    """
    Determines timedeltas that can be used to estimate when a file would
    be released and the date representing the last date in the file.

    Note: Current technique does not accurately reflect infrequent changes such
    as like DST changes or odd scheduling like not publishing on a weekend.
    """
    publish_interval = compute_interval(release_dates, tolerance)
    publish_offset = compute_offset(release_dates, publish_interval, tolerance)
    content_interval = compute_interval(content_end_dates, tolerance)
    content_offset = compute_content_offset(
        release_dates, content_end_dates, content_interval, tolerance,
    )
    return publish_interval, publish_offset, content_interval, content_offset
