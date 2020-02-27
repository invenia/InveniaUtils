import collections
import operator
from datetime import timedelta

from inveniautils.dates import round_datetime
from inveniautils.datetime_range import Bound, DatetimeRange
from inveniautils.iteration import aggregate

# Right now we only do period-ending aggregation. We may at some point
# want to do aggregations over a window occuring at a frequency. For example
#
# Given the simple dataset with a target date and a value:
# 2015/3/3 00:00, 1
# 2015/3/3 00:20, 2
# 2015/3/3 00:40, 3
# 2015/3/3 01:00, 4
#
# An hourly-ending aggregation could produce:
# 2015/3/3 00:00, [1]
# 2015/3/3 01:00, [2, 3, 4]
#
# Alternatively we could have a hourly-window taken every 30 minutes:
# 2015/3/3 00:00, [1]
# 2015/3/3 00:30, [1, 2]
# 2015/3/3 01:00, [2, 3, 4]
#
# Currently we don't have a use case for this.


class TimeSeriesAggregate(object):
    def __init__(
        self,
        aggregator,
        primary_keys,
        group_by,
        target_key,
        release_date_key,
        period=None,
        output_target_key=None,  # Rename the target_key field upon aggregation
        release_dates_reducer=None,
        start_inclusive=True,
        end_inclusive=False,
    ):
        if isinstance(primary_keys, str):
            primary_keys = (primary_keys,)

        if isinstance(group_by, str):
            group_by = (group_by,)

        self.primary_keys = primary_keys
        self.target_key = target_key
        self.release_date_key = release_date_key

        if output_target_key is not None:
            self.output_target_key = output_target_key
        else:
            self.output_target_key = target_key

        self.group_by = set(group_by) - set([target_key])
        self.unique_rd_key = operator.itemgetter(
            *(set(primary_keys) - set([release_date_key]))
        )

        self.aggregator = aggregator
        self.target_period = period
        self.release_dates_reducer = release_dates_reducer
        self.start_inclusive = start_inclusive
        self.end_inclusive = end_inclusive

    def grouping(self, row):
        if self.target_period is not None:
            period_end = round_datetime(
                row[self.target_key].end, self.target_period, ceil=True
            )
            period_start = round_datetime(
                period_end - self.target_period, self.target_period, ceil=True
            )

            start_inclusivity = (
                Bound.INCLUSIVE if self.start_inclusive else Bound.EXCLUSIVE
            )
            end_inclusivity = Bound.INCLUSIVE if self.end_inclusive else Bound.EXCLUSIVE
            group_target = DatetimeRange(
                period_start, period_end, (start_inclusivity, end_inclusivity)
            )
        else:
            group_target = row[self.target_key]

        # Equivalent to: [tuple({...}.items())]
        yield (
            ((self.output_target_key, group_target),)
            + tuple((k, row[k]) for k in self.group_by)
        )

    def averager(self, identifier, rows):
        row_release_dates = [row[self.release_date_key] for row in rows]
        if self.release_dates_reducer is not None:
            row_release_dates = self.release_dates_reducer(row_release_dates)

        unique_release_dates = sorted(set(row_release_dates))

        # Note: Shouldn't need OrderedDicts as unique_release_dates will keep
        # the release dates ordered and the ordering of the rows shouldn't
        # matter. That said `release_date: collections.OrderedDict()` is useful
        # for debugging and testing.
        versions = {
            release_date: collections.OrderedDict()
            for release_date in unique_release_dates
        }
        for row, row_release_date in zip(rows, row_release_dates):
            key = self.unique_rd_key(row)

            # Add row for each release date it preceeds. Since the rows are
            # ordered by (td, rd) only the latest rows should be present.
            for release_date in unique_release_dates:
                if row_release_date <= release_date:
                    versions[release_date][key] = row

        for release_date in unique_release_dates:
            versioned_id = dict(identifier)
            versioned_rows = versions[release_date].values()

            # Determine the latest release date within the versioned rows.
            # Note: we cannot trust the "release_date" to be realistic if it
            # has been manipulated.
            if self.release_dates_reducer is not None:
                latest_release_date = max(
                    row[self.release_date_key] for row in versioned_rows
                )
            else:
                latest_release_date = release_date

            versioned_id[self.release_date_key] = latest_release_date

            # Make sure to set the tage in the versioned id so that the
            # aggregator doesn't remove it
            versioned_id["tag"] = next(iter(versioned_rows)).get("tag", None)

            # Perform aggregation for each version
            result = self.aggregator(versioned_id, versioned_rows)

            # Allow aggregators to throw away rows if they wish
            if result is not None:
                yield result

    def relevant(self, key, element, element_keys):
        target_date = dict(key)[self.output_target_key]  # May be a range

        # As long as the newly processed element has a key that includes
        # the target date/range of the cached key the data is still relevant.
        for element_key in element_keys:
            element_target_date = dict(element_key)[self.output_target_key]
            if target_date == element_target_date:
                return True

        return False

    def __call__(self, iterator, relevancy_check=1000, debug=False):
        return aggregate(
            iterator,
            self.grouping,
            self.averager,
            relevancy_check=relevancy_check,  # Only exposed for testing
            relevant=self.relevant,
            complete=self.complete if hasattr(self, "complete") else None,
            debug=debug,
        )


def group_release_dates(period=timedelta(minutes=1)):
    """
    Reduces number of releases by grouping together all releases within
    a period of each other. For example 00:10 - 01:10 are within a one
    hour period of each other. Used with TimeSeriesAggregate as a
    "release_dates_reducer".
    """

    def period_release_dates(release_dates):
        results = []

        # Release dates may not be in ascending order but the loop below
        # needs to work on an ordered list.
        indices = sorted(range(len(release_dates)), key=lambda k: release_dates[k])
        limit = release_dates[0] + period
        for i in indices:
            release_date = release_dates[i]
            while release_date > limit:
                limit += period
            results.insert(i, limit)
        return results

    return period_release_dates


def latest_release_dates(release_dates):
    """
    Reduces the number of releases to only the latest release.
    Used with TimeSeriesAggregate as a "release_dates_reducer".

    WARNING: Do not use this function as is meant only for testing and
    emulating historical behaviour.
    """
    return [max(release_dates)] * len(release_dates)


# Extends the given dates further to correctly accommodate time series
# averaging over the entire period. We also need to be careful not to
# extend the range too far otherwise we could produce targets that were
# not requested by the user which can be problematic for layered feeds
def extend_date_range(date_range, period, bounds=None):
    if date_range is None:
        return date_range

    if not isinstance(date_range, DatetimeRange):
        raise ValueError("Expected a DatetimeRange")

    start = round_datetime(date_range.start, period, ceil=True)
    end = round_datetime(date_range.end, period, floor=True)

    # Include the previous period unless the start was not adjusted and
    # the start was already marked as exclusive.
    if not (start == date_range.start and not date_range.start_included):
        start = start - period
    # unless we specify ecplicit endpoint inclusivity for the
    # desired range, assume that they will match the inclusivity
    # of the input range
    if bounds is None:
        start_bound = date_range.start_bound
        end_bound = date_range.end_bound
    else:
        (start_bound, end_bound) = bounds

    return DatetimeRange(start=start, end=end, bounds=(start_bound, end_bound))
