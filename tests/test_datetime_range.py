"""
A collection of unittests for the timestamp's functions
"""
import logging
import unittest
from datetime import datetime, timedelta

from inveniautils.dates import localize
from inveniautils.datetime_range import (
    Bound,
    DatetimeRange,
    POS_INF_DATETIME,
    start_before_key,
    period_ending_as_range,
    period_beginning_as_range,
    cmp_ranges,
)

from dateutil.parser import parse as datetime_parser
from dateutil.relativedelta import relativedelta
import dateutil.tz
from dateutil.tz import tzoffset

import pytz

utc = pytz.utc
range_bounds = (Bound.INCLUSIVE, Bound.EXCLUSIVE)


class TestDatetimeRange(unittest.TestCase):
    def test_timezone_naive(self):
        """
        Creation of datetime range without timezones.
        """
        test = {"start": datetime.now() - timedelta(days=3), "end": datetime.now()}
        expected = [
            test["start"] + timedelta(days=0),
            test["start"] + timedelta(days=1),
            test["start"] + timedelta(days=2),
            test["start"] + timedelta(days=3),
        ]

        result = DatetimeRange(**test)

        self.assertEqual(result.start, test["start"])
        self.assertEqual(result.end, test["end"])
        self.assertEqual(result.tz_aware, False)
        self.assertEqual(result, result)
        self.assertEqual(list(result.dates(timedelta(days=1))), expected)

    def test_timezone_aware(self):
        """
        Creation of datetime range with timezones.
        """
        test = {
            "start": datetime(2013, 1, 1, tzinfo=utc),
            "end": datetime(2013, 1, 1, tzinfo=tzoffset("EST", -18000)),
        }
        expected = [
            datetime(2013, 1, 1, 0, tzinfo=utc),
            datetime(2013, 1, 1, 1, tzinfo=utc),
            datetime(2013, 1, 1, 2, tzinfo=utc),
            datetime(2013, 1, 1, 3, tzinfo=utc),
            datetime(2013, 1, 1, 4, tzinfo=utc),
            datetime(2013, 1, 1, 5, tzinfo=utc),
        ]

        result = DatetimeRange(**test)

        self.assertEqual(result.start, test["start"])
        self.assertEqual(result.end, test["end"])
        self.assertEqual(result.tz_aware, True)
        self.assertEqual(list(result.dates(timedelta(hours=1))), expected)

    def test_assign_start(self):
        """
        Datetime range assignment of start field.
        """
        dtr = DatetimeRange(
            start=datetime.now() - timedelta(days=3), end=datetime.now()
        )
        start_new = datetime.now() - timedelta(days=2)

        dtr.start = start_new
        self.assertEqual(dtr.start, start_new)

    def test_assign_end(self):
        """
        Datetime range assignment of end field.
        """
        dtr = DatetimeRange(
            start=datetime.now() - timedelta(days=3), end=datetime.now()
        )
        end_new = datetime.now() + timedelta(days=1)

        dtr.end = end_new
        self.assertEqual(dtr.end, end_new)

    def test_start_equals_end(self):
        """
        Datetime range where start == end.
        """
        dtr = DatetimeRange(start=datetime(2013, 1, 1), end=datetime(2013, 1, 1))
        expected = datetime(2013, 1, 1)

        self.assertEqual(list(dtr.dates(timedelta(days=1))), [expected])
        self.assertEqual(list(dtr.dates(timedelta(hours=1))), [expected])
        self.assertEqual(list(dtr.dates(timedelta(minutes=1))), [expected])
        self.assertEqual(list(dtr.dates(timedelta(seconds=1))), [expected])
        self.assertEqual(list(dtr.dates(timedelta(0))), [expected])

        self.assertEqual(list(dtr.ranges(timedelta(days=1))), [])
        self.assertEqual(list(dtr.ranges(timedelta(hours=1))), [])
        self.assertEqual(list(dtr.ranges(timedelta(minutes=1))), [])
        self.assertEqual(list(dtr.ranges(timedelta(seconds=1))), [])
        self.assertEqual(
            list(dtr.ranges(timedelta(0))),
            [DatetimeRange(expected, expected, range_bounds)],
        )

    def test_start_after_end(self):
        """
        Datetime range where start > end.
        """
        test = {"start": datetime(2013, 1, 2), "end": datetime(2013, 1, 1)}

        # TODO: Check error message?
        with self.assertRaises(ValueError):
            DatetimeRange(**test)

    def test_mix_timezone_awareness(self):
        """
        Datetime range using both timezone aware/unaware datetimes.
        """
        tz_naive = datetime(2013, 1, 1)
        tz_aware = datetime(2013, 1, 1, tzinfo=utc)

        # TODO: Check error message?
        with self.assertRaises(ValueError):
            DatetimeRange(start=tz_naive, end=tz_aware)

        # TODO: Check error message?
        with self.assertRaises(ValueError):
            DatetimeRange(start=tz_aware, end=tz_naive)

        # Attempt assign timezone aware datetime into a timezone naive range.
        dtr = DatetimeRange(start=tz_naive, end=tz_naive)
        self.assertEqual(dtr.tz_aware, False)

        with self.assertRaises(ValueError):
            dtr.start = tz_aware
        self.assertEqual(dtr.start, tz_naive)

        with self.assertRaises(ValueError):
            dtr.end = tz_aware
        self.assertEqual(dtr.end, tz_naive)

        # Attempt assign timezone naive datetime into a timezone aware range.
        dtr = DatetimeRange(start=tz_aware, end=tz_aware)
        self.assertEqual(dtr.tz_aware, True)

        with self.assertRaises(ValueError):
            dtr.start = tz_naive
        self.assertEqual(dtr.start, tz_aware)

        with self.assertRaises(ValueError):
            dtr.end = tz_naive
        self.assertEqual(dtr.end, tz_aware)

    def test_fromstring(self):
        """
        Creation of datetime range from a string.
        """
        test = "2012 to 2013"
        expected = DatetimeRange(start=datetime(2012, 1, 1), end=datetime(2013, 1, 1))

        result = DatetimeRange.fromstring(test)

        self.assertEqual(result.start, expected.start)
        self.assertEqual(result.end, expected.end)
        self.assertEqual(result.tz_aware, False)
        self.assertEqual(result, expected)

    def test_cast_to_naive(self):
        """
        Datetime range assignment of tz_aware field.
        """
        dtr = DatetimeRange(
            start=datetime(2013, 1, 1, tzinfo=utc),
            end=datetime(2013, 1, 1, tzinfo=tzoffset("EST", -18000)),
        )

        expected_aware = DatetimeRange(dtr.start, dtr.end)
        expected_naive = DatetimeRange(
            start=dtr.start.astimezone(utc).replace(tzinfo=None),
            end=dtr.end.astimezone(utc).replace(tzinfo=None),
        )
        expected_aware_dates = [
            datetime(2013, 1, 1, 0, tzinfo=utc),
            datetime(2013, 1, 1, 1, tzinfo=utc),
            datetime(2013, 1, 1, 2, tzinfo=utc),
            datetime(2013, 1, 1, 3, tzinfo=utc),
            datetime(2013, 1, 1, 4, tzinfo=utc),
            datetime(2013, 1, 1, 5, tzinfo=utc),
        ]
        expected_naive_dates = [dt.replace(tzinfo=None) for dt in expected_aware_dates]

        self.assertEqual(dtr.tz_aware, True)
        self.assertEqual(dtr.start, expected_aware.start)
        self.assertEqual(dtr.end, expected_aware.end)
        self.assertEqual(
            list(dtr.dates(timedelta(hours=1))), expected_aware_dates
        )  # noqa: E501
        self.assertEqual(dtr, expected_aware)

        dtr.tz_aware = False

        self.assertEqual(dtr.tz_aware, False)
        self.assertEqual(dtr.start, expected_naive.start)
        self.assertEqual(dtr.end, expected_naive.end)
        self.assertEqual(
            list(dtr.dates(timedelta(hours=1))), expected_naive_dates
        )  # noqa: E501
        self.assertEqual(dtr, expected_naive)

    def test_astimezone(self):
        """
        Datetime range usage of astimezone method.
        """
        dtr_aware = DatetimeRange(
            start=datetime(2013, 1, 1, tzinfo=utc),
            end=datetime(2013, 1, 1, tzinfo=tzoffset("EST", -18000)),
        )
        dtr_utc = dtr_aware.astimezone(utc)
        dtr_naive = DatetimeRange(start=datetime(2013, 1, 1), end=datetime(2013, 1, 1))

        expected_utc = DatetimeRange(
            start=datetime(2013, 1, 1, 0, tzinfo=utc),
            end=datetime(2013, 1, 1, 5, tzinfo=utc),
        )
        expected_aware_dates = [
            datetime(2013, 1, 1, 0, tzinfo=utc),
            datetime(2013, 1, 1, 1, tzinfo=utc),
            datetime(2013, 1, 1, 2, tzinfo=utc),
            datetime(2013, 1, 1, 3, tzinfo=utc),
            datetime(2013, 1, 1, 4, tzinfo=utc),
            datetime(2013, 1, 1, 5, tzinfo=utc),
        ]

        self.assertEqual(dtr_aware, dtr_utc)
        self.assertEqual(dtr_utc, expected_utc)
        self.assertEqual(list(dtr_utc.dates(timedelta(hours=1))), expected_aware_dates)

        with self.assertRaises(ValueError):
            dtr_naive.astimezone(utc)

    def test_dates_tz(self):
        """
        Datetime range into datetimes using timezones.
        """
        dtr_aware = DatetimeRange(
            start=datetime(2012, 12, 31, 19, tzinfo=tzoffset("EST", -18000)),
            end=datetime(2013, 1, 1, 0, tzinfo=tzoffset("EST", -18000)),
        )
        dtr_naive = DatetimeRange(start=datetime(2013, 1, 1), end=datetime(2013, 1, 1))
        expected_aware = DatetimeRange(
            start=datetime(2012, 12, 31, 19, tzinfo=tzoffset("EST", -18000)),
            end=datetime(2013, 1, 1, 0, tzinfo=tzoffset("EST", -18000)),
        )
        expected_aware_dates = [
            datetime(2013, 1, 1, 0, tzinfo=utc),
            datetime(2013, 1, 1, 1, tzinfo=utc),
            datetime(2013, 1, 1, 2, tzinfo=utc),
            datetime(2013, 1, 1, 3, tzinfo=utc),
            datetime(2013, 1, 1, 4, tzinfo=utc),
            datetime(2013, 1, 1, 5, tzinfo=utc),
        ]

        self.assertEqual(dtr_aware, expected_aware)
        self.assertEqual(
            list(dtr_aware.dates(timedelta(hours=1), tz=utc)), expected_aware_dates
        )

        with self.assertRaises(ValueError):
            list(dtr_naive.dates(timedelta(hours=1), tz=utc))

    def test_dates_pytz_dst_spring_hourly(self):
        """
        Converting datetime range into datetimes over spring DST
        transition using an hourly interval using pytz.

        Similar to testcase: test_dates_dateutil_dst_spring_hourly.
        """
        eastern = pytz.timezone("US/Eastern")
        test = {
            "start": localize(datetime(2013, 3, 10, 0), eastern),
            "end": localize(datetime(2013, 3, 10, 4), eastern),
        }
        expected = {
            "start": localize(datetime(2013, 3, 10, 0), eastern),
            "end": localize(datetime(2013, 3, 10, 4), eastern),
            "dates": [
                localize(datetime(2013, 3, 10, 0), eastern),
                localize(datetime(2013, 3, 10, 1), eastern),
                localize(datetime(2013, 3, 10, 3), eastern),
                localize(datetime(2013, 3, 10, 4), eastern),
            ],
            "ranges": [
                DatetimeRange(
                    localize(datetime(2013, 3, 10, 0), eastern),
                    localize(datetime(2013, 3, 10, 1), eastern),
                    range_bounds,
                ),
                DatetimeRange(
                    localize(datetime(2013, 3, 10, 1), eastern),
                    localize(datetime(2013, 3, 10, 3), eastern),
                    range_bounds,
                ),
                DatetimeRange(
                    localize(datetime(2013, 3, 10, 3), eastern),
                    localize(datetime(2013, 3, 10, 4), eastern),
                    range_bounds,
                ),
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(hours=1)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        self.assertEqual(dtr.start, expected["start"])
        self.assertEqual(dtr.end, expected["end"])

    # Fails due to 2013/3/10 02:00 being a created.
    @unittest.expectedFailure
    def test_dates_dateutil_dst_spring_hourly(self):
        """
        Converting datetime range into datetimes over spring DST
        transition using an hourly interval using dateutil.tz.

        Similar to testcase: test_dates_pytz_dst_spring_hourly.
        """
        eastern = dateutil.tz.gettz("US/Eastern")
        test = {
            "start": localize(datetime(2013, 3, 10, 0), eastern),
            "end": localize(datetime(2013, 3, 10, 4), eastern),
        }
        expected = {
            "start": localize(datetime(2013, 3, 10, 0), eastern),
            "end": localize(datetime(2013, 3, 10, 4), eastern),
            "dates": [
                localize(datetime(2013, 3, 10, 0), eastern),
                localize(datetime(2013, 3, 10, 1), eastern),
                localize(datetime(2013, 3, 10, 3), eastern),
                localize(datetime(2013, 3, 10, 4), eastern),
            ],
            "ranges": [
                DatetimeRange(
                    localize(datetime(2013, 3, 10, 0), eastern),
                    localize(datetime(2013, 3, 10, 1), eastern),
                    range_bounds,
                ),
                DatetimeRange(
                    localize(datetime(2013, 3, 10, 1), eastern),
                    localize(datetime(2013, 3, 10, 3), eastern),
                    range_bounds,
                ),
                DatetimeRange(
                    localize(datetime(2013, 3, 10, 3), eastern),
                    localize(datetime(2013, 3, 10, 4), eastern),
                    range_bounds,
                ),
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(hours=1)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        self.assertEqual(dtr.start, expected["start"])
        self.assertEqual(dtr.end, expected["end"])

    def test_dates_pytz_dst_fall_hourly(self):
        """
        Converting datetime range into datetimes over fall DST
        transition using an hourly interval using pytz.

        Similar to testcase: test_dates_dateutil_dst_fall_hourly.
        """
        eastern = pytz.timezone("US/Eastern")
        test = {
            "start": localize(datetime(2013, 11, 3, 0), eastern),
            "end": localize(datetime(2013, 11, 3, 4), eastern),
        }
        expected = {
            "start": localize(datetime(2013, 11, 3, 0), eastern),
            "end": localize(datetime(2013, 11, 3, 4), eastern),
            "dates": [
                localize(datetime(2013, 11, 3, 0), eastern, is_dst=None),
                localize(datetime(2013, 11, 3, 1), eastern, is_dst=True),
                localize(datetime(2013, 11, 3, 1), eastern, is_dst=False),
                localize(datetime(2013, 11, 3, 2), eastern, is_dst=None),
                localize(datetime(2013, 11, 3, 3), eastern, is_dst=None),
                localize(datetime(2013, 11, 3, 4), eastern, is_dst=None),
            ],
            "ranges": [
                DatetimeRange(
                    localize(datetime(2013, 11, 3, 0), eastern, is_dst=None),
                    localize(datetime(2013, 11, 3, 1), eastern, is_dst=True),
                    range_bounds,
                ),
                DatetimeRange(
                    localize(datetime(2013, 11, 3, 1), eastern, is_dst=True),
                    localize(datetime(2013, 11, 3, 1), eastern, is_dst=False),
                    range_bounds,
                ),
                DatetimeRange(
                    localize(datetime(2013, 11, 3, 1), eastern, is_dst=False),
                    localize(datetime(2013, 11, 3, 2), eastern, is_dst=None),
                    range_bounds,
                ),
                DatetimeRange(
                    localize(datetime(2013, 11, 3, 2), eastern, is_dst=None),
                    localize(datetime(2013, 11, 3, 3), eastern, is_dst=None),
                    range_bounds,
                ),
                DatetimeRange(
                    localize(datetime(2013, 11, 3, 3), eastern, is_dst=None),
                    localize(datetime(2013, 11, 3, 4), eastern, is_dst=None),
                    range_bounds,
                ),
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(hours=1)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        self.assertEqual(dtr.start, expected["start"])
        self.assertEqual(dtr.end, expected["end"])

    # Unable differentiate ambigious hours with dateutil.
    @unittest.expectedFailure
    def test_dates_dateutil_dst_fall_hourly(self):
        """
        Converting datetime range into datetimes over fall DST
        transition using an hourly interval using dateutil.

        Similar to testcase: test_dates_pytz_dst_fall_hourly.
        """
        eastern = dateutil.tz.gettz("US/Eastern")
        test = {
            "start": localize(datetime(2013, 11, 3, 0), eastern),
            "end": localize(datetime(2013, 11, 3, 4), eastern),
        }
        expected = {
            "start": localize(datetime(2013, 11, 3, 0), eastern),
            "end": localize(datetime(2013, 11, 3, 4), eastern),
            "dates": [
                datetime_parser("2013-11-03 00:00:00-04:00"),
                datetime_parser("2013-11-03 01:00:00-04:00"),
                datetime_parser("2013-11-03 01:00:00-05:00"),
                datetime_parser("2013-11-03 02:00:00-05:00"),
                datetime_parser("2013-11-03 03:00:00-05:00"),
                datetime_parser("2013-11-03 04:00:00-05:00"),
            ],
            "ranges": [
                DatetimeRange(
                    datetime_parser("2013-11-03 00:00:00-04:00"),
                    datetime_parser("2013-11-03 01:00:00-04:00"),
                    range_bounds,
                ),
                DatetimeRange(
                    datetime_parser("2013-11-03 01:00:00-04:00"),
                    datetime_parser("2013-11-03 01:00:00-05:00"),
                    range_bounds,
                ),
                DatetimeRange(
                    datetime_parser("2013-11-03 01:00:00-05:00"),
                    datetime_parser("2013-11-03 02:00:00-05:00"),
                    range_bounds,
                ),
                DatetimeRange(
                    datetime_parser("2013-11-03 02:00:00-05:00"),
                    datetime_parser("2013-11-03 03:00:00-05:00"),
                    range_bounds,
                ),
                DatetimeRange(
                    datetime_parser("2013-11-03 03:00:00-05:00"),
                    datetime_parser("2013-11-03 04:00:00-05:00"),
                    range_bounds,
                ),
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(hours=1)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        self.assertEqual(dtr.start, expected["start"])
        self.assertEqual(dtr.end, expected["end"])

    def test_dates_pytz_dst_spring_daily(self):
        """
        Converting datetime range into datetimes over spring DST
        transition using a daily interval using pytz.

        Note: The dates have been picked such that we need to produce a
        date on the non-existent spring hour 2013/3/10 02:00 US/Eastern.

        Similar to testcase: test_dates_dateutil_dst_spring_daily.
        """
        eastern = pytz.timezone("US/Eastern")
        test = {
            "start": localize(datetime(2013, 3, 9, 2), eastern),
            "end": localize(datetime(2013, 3, 11, 2), eastern),
        }
        expected = {
            "dates": [
                datetime_parser("2013-03-09 02:00:00-05:00"),
                datetime_parser("2013-03-10 02:00:00-05:00"),
                datetime_parser("2013-03-11 02:00:00-04:00"),
            ],
            "ranges": [
                DatetimeRange(
                    datetime_parser("2013-03-09 02:00:00-05:00"),
                    datetime_parser("2013-03-10 02:00:00-05:00"),
                    range_bounds,
                ),
                DatetimeRange(
                    datetime_parser("2013-03-10 02:00:00-05:00"),
                    datetime_parser("2013-03-11 02:00:00-04:00"),
                    range_bounds,
                ),
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(days=1)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        self.assertEqual(dtr.start, test["start"])
        self.assertEqual(dtr.end, test["end"])

    def test_dates_dateutil_dst_spring_daily(self):
        """
        Converting datetime range into datetimes over spring DST
        transition using a daily interval using dateutil.

        Note: The dates have been picked such that we need to produce a
        date on the non-existent spring hour 2013/3/10 02:00 US/Eastern.

        Similar to testcase: test_dates_pytz_dst_spring_daily.
        """
        eastern = dateutil.tz.gettz("US/Eastern")
        test = {
            "start": localize(datetime(2013, 3, 9, 2), eastern),
            "end": localize(datetime(2013, 3, 11, 2), eastern),
        }
        expected = {
            "dates": [
                datetime_parser("2013-03-09 02:00:00-05:00"),
                datetime_parser("2013-03-10 02:00:00-04:00"),
                datetime_parser("2013-03-11 02:00:00-04:00"),
            ],
            "ranges": [
                DatetimeRange(
                    datetime_parser("2013-03-09 02:00:00-05:00"),
                    datetime_parser("2013-03-10 02:00:00-04:00"),
                    range_bounds,
                ),
                DatetimeRange(
                    datetime_parser("2013-03-10 02:00:00-04:00"),
                    datetime_parser("2013-03-11 02:00:00-04:00"),
                    range_bounds,
                ),
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(days=1)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        self.assertEqual(dtr.start, test["start"])
        self.assertEqual(dtr.end, test["end"])

    def test_dates_pytz_dst_fall_daily(self):
        """
        Converting datetime range into datetimes over fall DST
        transition using a daily interval using pytz.

        Note: The dates have been picked such that we need to produce a
        date on the ambigious fall hour 2013/11/3 01:00 US/Eastern.

        Similar to testcase: test_dates_dateutil_dst_fall_daily.
        """
        eastern = pytz.timezone("US/Eastern")
        test = {
            "start": localize(datetime(2013, 11, 2, 1), eastern),
            "end": localize(datetime(2013, 11, 4, 1), eastern),
        }
        expected = {
            "dates": [
                datetime_parser("2013-11-02 01:00:00-04:00"),
                datetime_parser("2013-11-03 01:00:00-05:00"),
                datetime_parser("2013-11-04 01:00:00-05:00"),
            ],
            "ranges": [
                DatetimeRange(
                    datetime_parser("2013-11-02 01:00:00-04:00"),
                    datetime_parser("2013-11-03 01:00:00-05:00"),
                    range_bounds,
                ),
                DatetimeRange(
                    datetime_parser("2013-11-03 01:00:00-05:00"),
                    datetime_parser("2013-11-04 01:00:00-05:00"),
                    range_bounds,
                ),
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(days=1)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        self.assertEqual(dtr.start, test["start"])
        self.assertEqual(dtr.end, test["end"])

    @unittest.expectedFailure
    def test_dates_dateutil_dst_fall_daily(self):
        """
        Converting datetime range into datetimes over fall DST
        transition using a daily interval using dateutil.

        Note: The dates have been picked such that we need to produce a
        date on the ambigious fall hour 2013/11/3 01:00 US/Eastern.

        Similar to testcase: test_dates_pytz_dst_fall_daily.
        """
        eastern = dateutil.tz.gettz("US/Eastern")
        test = {
            "start": localize(datetime(2013, 11, 2, 1), eastern),
            "end": localize(datetime(2013, 11, 4, 1), eastern),
        }
        expected = {
            "dates": [
                dt.astimezone(eastern)
                for dt in [
                    datetime_parser("2013-11-02 01:00:00-04:00"),
                    datetime_parser("2013-11-03 01:00:00-05:00"),
                    datetime_parser("2013-11-04 01:00:00-05:00"),
                ]
            ],
            "ranges": [
                dtr.astimezone(eastern)
                for dtr in [
                    DatetimeRange(
                        datetime_parser("2013-11-02 01:00:00-04:00"),
                        datetime_parser("2013-11-03 01:00:00-05:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:00:00-05:00"),
                        datetime_parser("2013-11-04 01:00:00-05:00"),
                        range_bounds,
                    ),
                ]
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(days=1)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        self.assertEqual(dtr.start, test["start"])
        self.assertEqual(dtr.end, test["end"])

    def test_dates_pytz_dst_fall_edge_cases(self):
        """
        Converting datetime range into datetimes over fall DST
        transition using a two hour interval using pytz.

        Note: The dates have been picked such that we need to produce a
        date on the ambigious fall hour 2013/11/3 01:00 US/Eastern.

        Similar to testcase: test_dates_dateutil_dst_fall_edge_cases.
        """
        eastern = pytz.timezone("US/Eastern")

        # 2 hour interval
        test = {
            "start": localize(datetime(2013, 11, 2, 23), eastern),
            "end": localize(datetime(2013, 11, 3, 4), eastern),
        }
        expected = {
            "dates": [
                dt.astimezone(eastern)
                for dt in [
                    datetime_parser("2013-11-02 23:00:00-04:00"),
                    datetime_parser("2013-11-03 01:00:00-05:00"),
                    datetime_parser("2013-11-03 03:00:00-05:00"),
                ]
            ],
            "ranges": [
                r.astimezone(eastern)
                for r in [
                    DatetimeRange(
                        datetime_parser("2013-11-02 23:00:00-04:00"),
                        datetime_parser("2013-11-03 01:00:00-05:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:00:00-05:00"),
                        datetime_parser("2013-11-03 03:00:00-05:00"),
                        range_bounds,
                    ),
                ]
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(hours=2)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        # 59 minute interval
        test = {
            "start": localize(datetime(2013, 11, 3), eastern),
            "end": localize(datetime(2013, 11, 3, 3), eastern),
        }
        expected = {
            "dates": [
                dt.astimezone(eastern)
                for dt in [
                    datetime_parser("2013-11-03 00:00:00-04:00"),
                    datetime_parser("2013-11-03 00:59:00-04:00"),
                    datetime_parser("2013-11-03 01:58:00-04:00"),
                    datetime_parser("2013-11-03 01:57:00-05:00"),
                    datetime_parser("2013-11-03 02:56:00-05:00"),
                ]
            ],
            "ranges": [
                r.astimezone(eastern)
                for r in [
                    DatetimeRange(
                        datetime_parser("2013-11-03 00:00:00-04:00"),
                        datetime_parser("2013-11-03 00:59:00-04:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 00:59:00-04:00"),
                        datetime_parser("2013-11-03 01:58:00-04:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:58:00-04:00"),
                        datetime_parser("2013-11-03 01:57:00-05:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:57:00-05:00"),
                        datetime_parser("2013-11-03 02:56:00-05:00"),
                        range_bounds,
                    ),
                ]
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(minutes=59)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        # 1 hour and 1 minute interval
        test = {
            "start": localize(datetime(2013, 11, 2, 23, 59), eastern),
            "end": localize(datetime(2013, 11, 3, 3), eastern),
        }
        expected = {
            "dates": [
                dt.astimezone(eastern)
                for dt in [
                    datetime_parser("2013-11-02 23:59:00-04:00"),
                    datetime_parser("2013-11-03 01:00:00-04:00"),
                    datetime_parser("2013-11-03 01:01:00-05:00"),
                    datetime_parser("2013-11-03 02:02:00-05:00"),
                ]
            ],
            "ranges": [
                r.astimezone(eastern)
                for r in [
                    DatetimeRange(
                        datetime_parser("2013-11-02 23:59:00-04:00"),
                        datetime_parser("2013-11-03 01:00:00-04:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:00:00-04:00"),
                        datetime_parser("2013-11-03 01:01:00-05:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:01:00-05:00"),
                        datetime_parser("2013-11-03 02:02:00-05:00"),
                        range_bounds,
                    ),
                ]
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(hours=1, minutes=1)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

    @unittest.expectedFailure
    def test_dates_dateutil_dst_fall_edge_cases(self):
        """
        Converting datetime range into datetimes over fall DST
        transition using a two hour interval using dateutil.

        Note: The dates have been picked such that we need to produce a
        date on the ambigious fall hour 2013/11/3 01:00 US/Eastern.

        Similar to testcase: test_dates_pytz_dst_fall_edge_cases.
        """
        eastern = dateutil.tz.gettz("US/Eastern")

        # 2 hour interval
        test = {
            "start": localize(datetime(2013, 11, 2, 23), eastern),
            "end": localize(datetime(2013, 11, 3, 4), eastern),
        }
        expected = {
            "dates": [
                dt.astimezone(eastern)
                for dt in [
                    datetime_parser("2013-11-02 23:00:00-04:00"),
                    datetime_parser("2013-11-03 01:00:00-05:00"),
                    datetime_parser("2013-11-03 03:00:00-05:00"),
                ]
            ],
            "ranges": [
                r.astimezone(eastern)
                for r in [
                    DatetimeRange(
                        datetime_parser("2013-11-02 23:00:00-04:00"),
                        datetime_parser("2013-11-03 01:00:00-05:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:00:00-05:00"),
                        datetime_parser("2013-11-03 03:00:00-05:00"),
                        range_bounds,
                    ),
                ]
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(hours=2)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        # 59 minute interval
        test = {
            "start": localize(datetime(2013, 11, 3), eastern),
            "end": localize(datetime(2013, 11, 3, 3), eastern),
        }
        expected = {
            "dates": [
                dt.astimezone(eastern)
                for dt in [
                    datetime_parser("2013-11-03 00:00:00-04:00"),
                    datetime_parser("2013-11-03 00:59:00-04:00"),
                    datetime_parser("2013-11-03 01:58:00-04:00"),
                    datetime_parser("2013-11-03 01:57:00-05:00"),
                    datetime_parser("2013-11-03 02:56:00-05:00"),
                ]
            ],
            "ranges": [
                r.astimezone(eastern)
                for r in [
                    DatetimeRange(
                        datetime_parser("2013-11-03 00:00:00-04:00"),
                        datetime_parser("2013-11-03 00:59:00-04:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 00:59:00-04:00"),
                        datetime_parser("2013-11-03 01:58:00-04:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:58:00-04:00"),
                        datetime_parser("2013-11-03 01:57:00-05:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:57:00-05:00"),
                        datetime_parser("2013-11-03 02:56:00-05:00"),
                        range_bounds,
                    ),
                ]
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(minutes=59)

        dates = list(dtr.dates(interval))
        # self.assertEqual(dates, expected['dates'])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        # self.assertEqual(ranges, expected['ranges'])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

        # 1 hour and 1 minute interval
        test = {
            "start": localize(datetime(2013, 11, 2, 23, 59), eastern),
            "end": localize(datetime(2013, 11, 3, 3), eastern),
        }
        expected = {
            "dates": [
                dt.astimezone(eastern)
                for dt in [
                    datetime_parser("2013-11-02 23:59:00-04:00"),
                    datetime_parser("2013-11-03 01:00:00-04:00"),
                    datetime_parser("2013-11-03 01:01:00-05:00"),
                    datetime_parser("2013-11-03 02:02:00-05:00"),
                ]
            ],
            "ranges": [
                r.astimezone(eastern)
                for r in [
                    DatetimeRange(
                        datetime_parser("2013-11-02 23:59:00-04:00"),
                        datetime_parser("2013-11-03 01:00:00-04:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:00:00-04:00"),
                        datetime_parser("2013-11-03 01:01:00-05:00"),
                        range_bounds,
                    ),
                    DatetimeRange(
                        datetime_parser("2013-11-03 01:01:00-05:00"),
                        datetime_parser("2013-11-03 02:02:00-05:00"),
                        range_bounds,
                    ),
                ]
            ],
        }

        dtr = DatetimeRange(**test)
        interval = timedelta(hours=1, minutes=1)

        dates = list(dtr.dates(interval))
        self.assertEqual(dates, expected["dates"])
        for i in range(len(dates)):
            self.assertEqual(str(dates[i]), str(expected["dates"][i]))

        ranges = list(dtr.ranges(interval))
        self.assertEqual(ranges, expected["ranges"])
        for i in range(len(ranges)):
            self.assertEqual(str(ranges[i]), str(expected["ranges"][i]))

    def test_dates_zero_interval(self):
        dtr = DatetimeRange(start=datetime(2013, 1, 1), end=datetime(2013, 1, 2))

        self.assertEqual(list(dtr.dates(timedelta(0))), [datetime(2013, 1, 1)])
        self.assertEqual(
            list(dtr.dates(timedelta(0), reverse=True)), [datetime(2013, 1, 2)]
        )

        self.assertEqual(
            list(dtr.ranges(timedelta(0))),
            [DatetimeRange(datetime(2013, 1, 1), datetime(2013, 1, 1), range_bounds)],
        )
        self.assertEqual(
            list(dtr.ranges(timedelta(0), reverse=True)),
            [DatetimeRange(datetime(2013, 1, 2), datetime(2013, 1, 2), range_bounds)],
        )

    def test_dates_reversed(self):
        dtr = DatetimeRange(start=datetime(2013, 1, 1), end=datetime(2013, 1, 3))

        self.assertEqual(
            list(dtr.dates(timedelta(days=1), True)),
            [datetime(2013, 1, 3), datetime(2013, 1, 2), datetime(2013, 1, 1)],
        )

        dtr = DatetimeRange(
            start=datetime(2013, 1, 1),
            end=datetime(2013, 1, 3),
            bounds=(Bound.INCLUSIVE, Bound.EXCLUSIVE),
        )

        self.assertEqual(
            list(dtr.dates(timedelta(days=1), True)),
            [datetime(2013, 1, 2), datetime(2013, 1, 1)],
        )

    def test_dates_negative_interval(self):
        dtr = DatetimeRange(start=datetime(2013, 1, 1), end=datetime(2013, 1, 2))

        with self.assertRaises(ValueError):
            next(dtr.dates(timedelta(seconds=-1)))

        with self.assertRaises(ValueError):
            next(dtr.ranges(timedelta(seconds=-1)))

    def test_ranges_bounds_exclusive(self):
        dtr = DatetimeRange(
            start=datetime(2013, 1, 1, 0),
            end=datetime(2013, 1, 1, 3),
            bounds=(Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )
        period = timedelta(hours=1)

        def output(rang, bounds):
            dates = [
                datetime(2013, 1, 1, 0),
                datetime(2013, 1, 1, 1),
                datetime(2013, 1, 1, 2),
                datetime(2013, 1, 1, 3),
            ]
            rang = list(rang)
            last = rang[0]
            for i in rang[1:]:
                yield DatetimeRange(dates[last], dates[i], bounds)
                last = i

        bounds = (Bound.INCLUSIVE, Bound.INCLUSIVE)
        self.assertEqual(
            list(dtr.ranges(period, bounds=bounds)), list(output(range(1, 3), bounds))
        )

        bounds = (Bound.EXCLUSIVE, Bound.INCLUSIVE)
        self.assertEqual(
            list(dtr.ranges(period, bounds=bounds)), list(output(range(0, 3), bounds))
        )

        bounds = (Bound.INCLUSIVE, Bound.EXCLUSIVE)
        self.assertEqual(
            list(dtr.ranges(period, bounds=bounds)), list(output(range(1, 4), bounds))
        )

        bounds = (Bound.EXCLUSIVE, Bound.EXCLUSIVE)
        self.assertEqual(
            list(dtr.ranges(period, bounds=bounds)), list(output(range(0, 4), bounds))
        )

    def test_containing(self):
        """
        Creation of dateime range via containing.

        Visualization of the test range used:

          (23)
        (01)
            3
        """
        test = [
            DatetimeRange(
                datetime(2013, 1, 1, 2), datetime(2013, 1, 1, 3), Bound.EXCLUSIVE
            ),
            DatetimeRange(
                datetime(2013, 1, 1, 0), datetime(2013, 1, 1, 1), Bound.EXCLUSIVE
            ),
            datetime(2013, 1, 1, 3),
        ]
        expected = DatetimeRange(
            datetime(2013, 1, 1, 0),
            datetime(2013, 1, 1, 3),
            (Bound.EXCLUSIVE, Bound.INCLUSIVE),
        )

        result = DatetimeRange.containing(test)
        self.assertEqual(result, expected)

    def test_reduce(self):
        """
        Creation of datetime range via reduce.

        Visualization of the test range used:

        [01]
         [123]
          [234]
        """
        test = [
            DatetimeRange(datetime(2012, 1, 1, 0), datetime(2013, 1, 1, 1)),
            DatetimeRange(datetime(2012, 1, 1, 1), datetime(2013, 1, 1, 3)),
            DatetimeRange(datetime(2012, 1, 1, 2), datetime(2013, 1, 1, 4)),
        ]
        expected = [DatetimeRange(datetime(2012, 1, 1, 0), datetime(2013, 1, 1, 4))]

        result = list(DatetimeRange.reduce(test))
        self.assertEqual(result, expected)

    def test_reduce_with_bounds(self):
        """
        Creation of datetime range via reduce respects bounds.

        Make sure that reducing notices changes in bound types.

        Visualization of the test range used:

        [123]
        (12345]
        [12345)
          (345)
        """
        test = [
            DatetimeRange(
                datetime(2012, 1, 1),
                datetime(2012, 1, 3),
                (Bound.INCLUSIVE, Bound.INCLUSIVE),
            ),
            DatetimeRange(
                datetime(2012, 1, 1),
                datetime(2012, 1, 5),
                (Bound.EXCLUSIVE, Bound.INCLUSIVE),
            ),
            DatetimeRange(
                datetime(2012, 1, 1),
                datetime(2012, 1, 5),
                (Bound.INCLUSIVE, Bound.EXCLUSIVE),
            ),
            DatetimeRange(
                datetime(2012, 1, 3),
                datetime(2012, 1, 5),
                (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
            ),
        ]

        expected = [
            DatetimeRange(
                datetime(2012, 1, 1),
                datetime(2012, 1, 5),
                (Bound.INCLUSIVE, Bound.INCLUSIVE),
            )
        ]

        result = list(DatetimeRange.reduce(test))
        self.assertEqual(result, expected)

    def test_reduce_with_exclusive_bounds(self):
        """
        Creation of datetime range via reduce on non-inclusive touching ranges.

        Make sure that reduce does not combine an exclusive end with an
        exclusive start which containing the same datetime.

        Visualization of the test range used:

        (12)
          (34)
         [23)
        """
        test = [
            DatetimeRange(
                datetime(2012, 1, 1),
                datetime(2012, 1, 2),
                (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
            ),
            DatetimeRange(
                datetime(2012, 1, 3),
                datetime(2012, 1, 4),
                (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
            ),
            DatetimeRange(
                datetime(2012, 1, 2),
                datetime(2012, 1, 3),
                (Bound.INCLUSIVE, Bound.EXCLUSIVE),
            ),
        ]

        expected = [
            DatetimeRange(
                datetime(2012, 1, 1),
                datetime(2012, 1, 3),
                (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
            ),
            DatetimeRange(
                datetime(2012, 1, 3),
                datetime(2012, 1, 4),
                (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
            ),
        ]

        result = list(DatetimeRange.reduce(test))
        self.assertEqual(result, expected)

    def test_aligned(self):
        test = DatetimeRange(datetime(2012, 1, 1, 2, 3, 4), datetime(2012, 1, 2))

        self.assertEqual(
            test.aligned(timedelta(days=1)),
            DatetimeRange(datetime(2012, 1, 1), datetime(2012, 1, 2)),
        )
        self.assertEqual(
            test.aligned(timedelta(hours=1)),
            DatetimeRange(datetime(2012, 1, 1, 2), datetime(2012, 1, 2)),
        )
        self.assertEqual(
            test.aligned(timedelta(minutes=1)),
            DatetimeRange(datetime(2012, 1, 1, 2, 3), datetime(2012, 1, 2)),
        )

    def test_non_overlapping(self):
        """
        Comparisons on non-overlapping datetime ranges.

        Visualization of the test range used:

        [12]
           [345]
        """
        earlier = DatetimeRange(datetime(2012, 1, 1), datetime(2012, 1, 2))
        later = DatetimeRange(datetime(2012, 1, 3), datetime(2012, 1, 5))

        self.assertTrue(earlier.before_disjoint(later))
        self.assertFalse(later.before_disjoint(earlier))
        self.assertFalse(earlier.after_disjoint(later))
        self.assertTrue(later.after_disjoint(earlier))

        self.assertFalse(earlier.before_overlaps(later))
        self.assertFalse(later.before_overlaps(earlier))
        self.assertFalse(earlier.after_overlaps(later))
        self.assertFalse(later.after_overlaps(earlier))

        self.assertFalse(earlier.before_touching(later))
        self.assertFalse(later.before_touching(earlier))
        self.assertFalse(earlier.after_touching(later))
        self.assertFalse(later.after_touching(earlier))

        self.assertTrue(earlier.starts_before(later))
        self.assertFalse(later.starts_before(earlier))
        self.assertFalse(earlier.starts_after(later))
        self.assertTrue(later.starts_after(earlier))

        self.assertTrue(earlier.ends_before(later))
        self.assertFalse(later.ends_before(earlier))
        self.assertFalse(earlier.ends_after(later))
        self.assertTrue(later.ends_after(earlier))

        self.assertFalse(earlier.overlaps(later))
        self.assertFalse(later.overlaps(earlier))

        self.assertFalse(earlier.contains(later))
        self.assertFalse(later.contains(earlier))

        self.assertFalse(earlier in later)
        self.assertFalse(later in earlier)

        self.assertTrue(start_before_key(earlier) < start_before_key(later))
        self.assertFalse(start_before_key(later) < start_before_key(earlier))

        with self.assertRaises(NotImplementedError):
            earlier < later
        with self.assertRaises(NotImplementedError):
            earlier > later
        with self.assertRaises(NotImplementedError):
            earlier <= later
        with self.assertRaises(NotImplementedError):
            earlier >= later

        with self.assertRaises(ValueError):
            earlier.overlapping_range(later)
        with self.assertRaises(ValueError):
            later.overlapping_range(earlier)

    def test_touching_bounds_exclusive(self):
        """
        Comparisons on touching datetime ranges (EE).

        Visualization of the test range used:

        (123)
          (345)
        """
        earlier = DatetimeRange(
            datetime(2012, 1, 1), datetime(2012, 1, 3), Bound.EXCLUSIVE
        )
        later = DatetimeRange(
            datetime(2012, 1, 3), datetime(2012, 1, 5), Bound.EXCLUSIVE
        )

        self.assertTrue(earlier.before_disjoint(later))
        self.assertFalse(later.before_disjoint(earlier))
        self.assertFalse(earlier.after_disjoint(later))
        self.assertTrue(later.after_disjoint(earlier))

        self.assertFalse(earlier.before_overlaps(later))
        self.assertFalse(later.before_overlaps(earlier))
        self.assertFalse(earlier.after_overlaps(later))
        self.assertFalse(later.after_overlaps(earlier))

        self.assertFalse(earlier.before_touching(later))
        self.assertFalse(later.before_touching(earlier))
        self.assertFalse(earlier.after_touching(later))
        self.assertFalse(later.after_touching(earlier))

        self.assertTrue(earlier.starts_before(later))
        self.assertFalse(later.starts_before(earlier))
        self.assertFalse(earlier.starts_after(later))
        self.assertTrue(later.starts_after(earlier))

        self.assertTrue(earlier.ends_before(later))
        self.assertFalse(later.ends_before(earlier))
        self.assertFalse(earlier.ends_after(later))
        self.assertTrue(later.ends_after(earlier))

        self.assertFalse(earlier.overlaps(later))
        self.assertFalse(later.overlaps(earlier))

        self.assertFalse(earlier.contains(later))
        self.assertFalse(later.contains(earlier))

        self.assertFalse(earlier in later)
        self.assertFalse(later in earlier)

        self.assertTrue(start_before_key(earlier) < start_before_key(later))
        self.assertFalse(start_before_key(later) < start_before_key(earlier))

        with self.assertRaises(NotImplementedError):
            earlier < later
        with self.assertRaises(NotImplementedError):
            earlier > later
        with self.assertRaises(NotImplementedError):
            earlier <= later
        with self.assertRaises(NotImplementedError):
            earlier >= later

        with self.assertRaises(ValueError):
            earlier.overlapping_range(later)
        with self.assertRaises(ValueError):
            later.overlapping_range(earlier)

    def test_touching_bounds_exclusive_inclusive(self):
        """
        Comparisons on touching datetime ranges (EI).

        Visualization of the test range used:

        (123)
          [345]
        """
        earlier = DatetimeRange(
            datetime(2012, 1, 1), datetime(2012, 1, 3), Bound.EXCLUSIVE
        )
        later = DatetimeRange(
            datetime(2012, 1, 3), datetime(2012, 1, 5), Bound.INCLUSIVE
        )

        self.assertTrue(earlier.before_disjoint(later))
        self.assertFalse(later.before_disjoint(earlier))
        self.assertFalse(earlier.after_disjoint(later))
        self.assertTrue(later.after_disjoint(earlier))

        self.assertFalse(earlier.before_overlaps(later))
        self.assertFalse(later.before_overlaps(earlier))
        self.assertFalse(earlier.after_overlaps(later))
        self.assertFalse(later.after_overlaps(earlier))

        self.assertTrue(earlier.before_touching(later))
        self.assertFalse(later.before_touching(earlier))
        self.assertFalse(earlier.after_touching(later))
        self.assertTrue(later.after_touching(earlier))

        self.assertTrue(earlier.starts_before(later))
        self.assertFalse(later.starts_before(earlier))
        self.assertFalse(earlier.starts_after(later))
        self.assertTrue(later.starts_after(earlier))

        self.assertTrue(earlier.ends_before(later))
        self.assertFalse(later.ends_before(earlier))
        self.assertFalse(earlier.ends_after(later))
        self.assertTrue(later.ends_after(earlier))

        self.assertFalse(earlier.overlaps(later))
        self.assertFalse(later.overlaps(earlier))

        self.assertFalse(earlier.contains(later))
        self.assertFalse(later.contains(earlier))

        self.assertFalse(earlier in later)
        self.assertFalse(later in earlier)

        self.assertTrue(start_before_key(earlier) < start_before_key(later))
        self.assertFalse(start_before_key(later) < start_before_key(earlier))

        with self.assertRaises(NotImplementedError):
            earlier < later
        with self.assertRaises(NotImplementedError):
            earlier > later
        with self.assertRaises(NotImplementedError):
            earlier <= later
        with self.assertRaises(NotImplementedError):
            earlier >= later

        with self.assertRaises(ValueError):
            earlier.overlapping_range(later)
        with self.assertRaises(ValueError):
            later.overlapping_range(earlier)

    def test_touching_bounds_inclusive_exclusive(self):
        """
        Comparisons on touching datetime ranges (IE).

        Visualization of the test range used:

        [123]
          (345)
        """
        earlier = DatetimeRange(
            datetime(2012, 1, 1), datetime(2012, 1, 3), Bound.INCLUSIVE
        )
        later = DatetimeRange(
            datetime(2012, 1, 3), datetime(2012, 1, 5), Bound.EXCLUSIVE
        )

        self.assertTrue(earlier.before_disjoint(later))
        self.assertFalse(later.before_disjoint(earlier))
        self.assertFalse(earlier.after_disjoint(later))
        self.assertTrue(later.after_disjoint(earlier))

        self.assertFalse(earlier.before_overlaps(later))
        self.assertFalse(later.before_overlaps(earlier))
        self.assertFalse(earlier.after_overlaps(later))
        self.assertFalse(later.after_overlaps(earlier))

        self.assertTrue(earlier.before_touching(later))
        self.assertFalse(later.before_touching(earlier))
        self.assertFalse(earlier.after_touching(later))
        self.assertTrue(later.after_touching(earlier))

        self.assertTrue(earlier.starts_before(later))
        self.assertFalse(later.starts_before(earlier))
        self.assertFalse(earlier.starts_after(later))
        self.assertTrue(later.starts_after(earlier))

        self.assertTrue(earlier.ends_before(later))
        self.assertFalse(later.ends_before(earlier))
        self.assertFalse(earlier.ends_after(later))
        self.assertTrue(later.ends_after(earlier))

        self.assertFalse(earlier.overlaps(later))
        self.assertFalse(later.overlaps(earlier))

        self.assertFalse(earlier.contains(later))
        self.assertFalse(later.contains(earlier))

        self.assertFalse(earlier in later)
        self.assertFalse(later in earlier)

        self.assertTrue(start_before_key(earlier) < start_before_key(later))
        self.assertFalse(start_before_key(later) < start_before_key(earlier))

        with self.assertRaises(NotImplementedError):
            earlier < later
        with self.assertRaises(NotImplementedError):
            earlier > later
        with self.assertRaises(NotImplementedError):
            earlier <= later
        with self.assertRaises(NotImplementedError):
            earlier >= later

        with self.assertRaises(ValueError):
            earlier.overlapping_range(later)
        with self.assertRaises(ValueError):
            later.overlapping_range(earlier)

    def test_touching_bounds_inclusive(self):
        """
        Comparisons on touching datetime ranges (II).

        Visualization of the test range used:

        [123]
          [345)
        """
        earlier = DatetimeRange(
            datetime(2012, 1, 1), datetime(2012, 1, 3), Bound.INCLUSIVE
        )
        later = DatetimeRange(
            datetime(2012, 1, 3), datetime(2012, 1, 5), Bound.INCLUSIVE
        )

        self.assertFalse(earlier.before_disjoint(later))
        self.assertFalse(later.before_disjoint(earlier))
        self.assertFalse(earlier.after_disjoint(later))
        self.assertFalse(later.after_disjoint(earlier))

        self.assertTrue(earlier.before_overlaps(later))
        self.assertFalse(later.before_overlaps(earlier))
        self.assertFalse(earlier.after_overlaps(later))
        self.assertTrue(later.after_overlaps(earlier))

        self.assertTrue(earlier.before_touching(later))
        self.assertFalse(later.before_touching(earlier))
        self.assertFalse(earlier.after_touching(later))
        self.assertTrue(later.after_touching(earlier))

        self.assertTrue(earlier.starts_before(later))
        self.assertFalse(later.starts_before(earlier))
        self.assertFalse(earlier.starts_after(later))
        self.assertTrue(later.starts_after(earlier))

        self.assertTrue(earlier.ends_before(later))
        self.assertFalse(later.ends_before(earlier))
        self.assertFalse(earlier.ends_after(later))
        self.assertTrue(later.ends_after(earlier))

        self.assertTrue(earlier.overlaps(later))
        self.assertTrue(later.overlaps(earlier))

        self.assertFalse(earlier.contains(later))
        self.assertFalse(later.contains(earlier))

        self.assertFalse(earlier in later)
        self.assertFalse(later in earlier)

        self.assertTrue(start_before_key(earlier) < start_before_key(later))
        self.assertFalse(start_before_key(later) < start_before_key(earlier))

        with self.assertRaises(NotImplementedError):
            earlier < later
        with self.assertRaises(NotImplementedError):
            earlier > later
        with self.assertRaises(NotImplementedError):
            earlier <= later
        with self.assertRaises(NotImplementedError):
            earlier >= later

        overlap = DatetimeRange(
            datetime(2012, 1, 3), datetime(2012, 1, 3), Bound.INCLUSIVE
        )
        self.assertEqual(earlier.overlapping_range(later), overlap)
        self.assertEqual(later.overlapping_range(earlier), overlap)

    def test_overlapping(self):
        """
        Comparisons on overlapping datetime ranges.

        Visualization of the test range used:

        [1234]
         [2345]
        """
        earlier = DatetimeRange(datetime(2012, 1, 1), datetime(2012, 1, 4))
        later = DatetimeRange(datetime(2012, 1, 2), datetime(2012, 1, 5))

        self.assertFalse(earlier.before_disjoint(later))
        self.assertFalse(later.before_disjoint(earlier))
        self.assertFalse(earlier.after_disjoint(later))
        self.assertFalse(later.after_disjoint(earlier))

        self.assertTrue(earlier.before_overlaps(later))
        self.assertFalse(later.before_overlaps(earlier))
        self.assertFalse(earlier.after_overlaps(later))
        self.assertTrue(later.after_overlaps(earlier))

        self.assertFalse(earlier.before_touching(later))
        self.assertFalse(later.before_touching(earlier))
        self.assertFalse(earlier.after_touching(later))
        self.assertFalse(later.after_touching(earlier))

        self.assertTrue(earlier.starts_before(later))
        self.assertFalse(later.starts_before(earlier))
        self.assertFalse(earlier.starts_after(later))
        self.assertTrue(later.starts_after(earlier))

        self.assertTrue(earlier.ends_before(later))
        self.assertFalse(later.ends_before(earlier))
        self.assertFalse(earlier.ends_after(later))
        self.assertTrue(later.ends_after(earlier))

        self.assertTrue(earlier.overlaps(later))
        self.assertTrue(later.overlaps(earlier))

        self.assertFalse(earlier.contains(later))
        self.assertFalse(later.contains(earlier))

        self.assertFalse(earlier in later)
        self.assertFalse(later in earlier)

        self.assertTrue(start_before_key(earlier) < start_before_key(later))
        self.assertFalse(start_before_key(later) < start_before_key(earlier))

        with self.assertRaises(NotImplementedError):
            earlier < later
        with self.assertRaises(NotImplementedError):
            earlier > later
        with self.assertRaises(NotImplementedError):
            earlier <= later
        with self.assertRaises(NotImplementedError):
            earlier >= later

        overlap = DatetimeRange(datetime(2012, 1, 2), datetime(2012, 1, 4))
        self.assertEqual(earlier.overlapping_range(later), overlap)
        self.assertEqual(later.overlapping_range(earlier), overlap)

    def test_equality_ee_ee(self):
        """
        Comparisons on ranges with equal respective start and end (EE EE).
        """
        # a = (x,y), b = (x,y)
        a = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )
        b = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )

        self.assertFalse(a.before_disjoint(b))
        self.assertFalse(b.before_disjoint(a))
        self.assertFalse(a.after_disjoint(b))
        self.assertFalse(b.after_disjoint(a))

        self.assertFalse(a.before_overlaps(b))
        self.assertFalse(b.before_overlaps(a))
        self.assertFalse(a.after_overlaps(b))
        self.assertFalse(b.after_overlaps(a))

        self.assertFalse(a.before_touching(b))
        self.assertFalse(b.before_touching(a))
        self.assertFalse(a.after_touching(b))
        self.assertFalse(b.after_touching(a))

        self.assertFalse(a.starts_before(b))
        self.assertFalse(b.starts_before(a))
        self.assertFalse(a.starts_after(b))
        self.assertFalse(b.starts_after(a))

        self.assertFalse(a.ends_before(b))
        self.assertFalse(b.ends_before(a))
        self.assertFalse(a.ends_after(b))
        self.assertFalse(b.ends_after(a))

        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

        self.assertTrue(a.contains(b))
        self.assertTrue(b.contains(a))

        self.assertTrue(a in b)
        self.assertTrue(b in a)

        self.assertFalse(start_before_key(a) < start_before_key(b))
        self.assertFalse(start_before_key(b) < start_before_key(a))

        with self.assertRaises(NotImplementedError):
            a < b
        with self.assertRaises(NotImplementedError):
            a > b
        with self.assertRaises(NotImplementedError):
            a <= b
        with self.assertRaises(NotImplementedError):
            a >= b

        overlap = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )
        self.assertEqual(a.overlapping_range(b), overlap)
        self.assertEqual(b.overlapping_range(a), overlap)

    def test_equality_ie_ee(self):
        """
        Comparisons on ranges with equal respective start and end (IE EE).
        """
        # a = [x,y), b = (x,y)
        a = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.INCLUSIVE, Bound.EXCLUSIVE),
        )
        b = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )

        self.assertFalse(a.before_disjoint(b))
        self.assertFalse(b.before_disjoint(a))
        self.assertFalse(a.after_disjoint(b))
        self.assertFalse(b.after_disjoint(a))

        self.assertTrue(a.before_overlaps(b))
        self.assertFalse(b.before_overlaps(a))
        self.assertFalse(a.after_overlaps(b))
        self.assertTrue(b.after_overlaps(a))

        self.assertFalse(a.before_touching(b))
        self.assertFalse(b.before_touching(a))
        self.assertFalse(a.after_touching(b))
        self.assertFalse(b.after_touching(a))

        self.assertTrue(a.starts_before(b))
        self.assertFalse(b.starts_before(a))
        self.assertFalse(a.starts_after(b))
        self.assertTrue(b.starts_after(a))

        self.assertFalse(a.ends_before(b))
        self.assertFalse(b.ends_before(a))
        self.assertFalse(a.ends_after(b))
        self.assertFalse(b.ends_after(a))

        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

        self.assertTrue(a.contains(b))
        self.assertFalse(b.contains(a))

        self.assertFalse(a in b)
        self.assertTrue(b in a)

        self.assertTrue(start_before_key(a) < start_before_key(b))
        self.assertFalse(start_before_key(b) < start_before_key(a))

        with self.assertRaises(NotImplementedError):
            a < b
        with self.assertRaises(NotImplementedError):
            a > b
        with self.assertRaises(NotImplementedError):
            a <= b
        with self.assertRaises(NotImplementedError):
            a >= b

        overlap = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )
        self.assertEqual(a.overlapping_range(b), overlap)
        self.assertEqual(b.overlapping_range(a), overlap)

    def test_equality_ei_ee(self):
        """
        Comparisons on ranges with equal respective start and end (EI EE).
        """
        # a = (x,y], b = (x,y)
        a = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.INCLUSIVE),
        )
        b = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )

        self.assertFalse(a.before_disjoint(b))
        self.assertFalse(b.before_disjoint(a))
        self.assertFalse(a.after_disjoint(b))
        self.assertFalse(b.after_disjoint(a))

        self.assertFalse(a.before_overlaps(b))
        self.assertFalse(b.before_overlaps(a))
        self.assertFalse(a.after_overlaps(b))
        self.assertFalse(b.after_overlaps(a))

        self.assertFalse(a.before_touching(b))
        self.assertFalse(b.before_touching(a))
        self.assertFalse(a.after_touching(b))
        self.assertFalse(b.after_touching(a))

        self.assertFalse(a.starts_before(b))
        self.assertFalse(b.starts_before(a))
        self.assertFalse(a.starts_after(b))
        self.assertFalse(b.starts_after(a))

        self.assertFalse(a.ends_before(b))
        self.assertTrue(b.ends_before(a))
        self.assertTrue(a.ends_after(b))
        self.assertFalse(b.ends_after(a))

        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

        self.assertTrue(a.contains(b))
        self.assertFalse(b.contains(a))

        self.assertFalse(a in b)
        self.assertTrue(b in a)

        self.assertFalse(start_before_key(a) < start_before_key(b))
        self.assertFalse(start_before_key(b) < start_before_key(a))

        with self.assertRaises(NotImplementedError):
            a < b
        with self.assertRaises(NotImplementedError):
            a > b
        with self.assertRaises(NotImplementedError):
            a <= b
        with self.assertRaises(NotImplementedError):
            a >= b

        overlap = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )
        self.assertEqual(a.overlapping_range(b), overlap)
        self.assertEqual(b.overlapping_range(a), overlap)

    def test_equality_ii_ee(self):
        """
        Comparisons on ranges with equal respective start and end (II EE).
        """
        # a = [x,y], b = (x,y)
        a = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )
        b = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )

        self.assertFalse(a.before_disjoint(b))
        self.assertFalse(b.before_disjoint(a))
        self.assertFalse(a.after_disjoint(b))
        self.assertFalse(b.after_disjoint(a))

        self.assertFalse(a.before_overlaps(b))
        self.assertFalse(b.before_overlaps(a))
        self.assertFalse(a.after_overlaps(b))
        self.assertFalse(b.after_overlaps(a))

        self.assertFalse(a.before_touching(b))
        self.assertFalse(b.before_touching(a))
        self.assertFalse(a.after_touching(b))
        self.assertFalse(b.after_touching(a))

        self.assertTrue(a.starts_before(b))
        self.assertFalse(b.starts_before(a))
        self.assertFalse(a.starts_after(b))
        self.assertTrue(b.starts_after(a))

        self.assertFalse(a.ends_before(b))
        self.assertTrue(b.ends_before(a))
        self.assertTrue(a.ends_after(b))
        self.assertFalse(b.ends_after(a))

        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

        self.assertTrue(a.contains(b))
        self.assertFalse(b.contains(a))

        self.assertFalse(a in b)
        self.assertTrue(b in a)

        self.assertTrue(start_before_key(a) < start_before_key(b))
        self.assertFalse(start_before_key(b) < start_before_key(a))

        with self.assertRaises(NotImplementedError):
            a < b
        with self.assertRaises(NotImplementedError):
            a > b
        with self.assertRaises(NotImplementedError):
            a <= b
        with self.assertRaises(NotImplementedError):
            a >= b

        overlap = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )
        self.assertEqual(a.overlapping_range(b), overlap)
        self.assertEqual(b.overlapping_range(a), overlap)

    def test_equality_ie_ii(self):
        """
        Comparisons on ranges with equal respective start and end (IE II).
        """
        # a = [x,y), b = [x,y]
        a = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.INCLUSIVE, Bound.EXCLUSIVE),
        )
        b = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )

        self.assertFalse(a.before_disjoint(b))
        self.assertFalse(b.before_disjoint(a))
        self.assertFalse(a.after_disjoint(b))
        self.assertFalse(b.after_disjoint(a))

        self.assertFalse(a.before_overlaps(b))
        self.assertFalse(b.before_overlaps(a))
        self.assertFalse(a.after_overlaps(b))
        self.assertFalse(b.after_overlaps(a))

        self.assertFalse(a.before_touching(b))
        self.assertFalse(b.before_touching(a))
        self.assertFalse(a.after_touching(b))
        self.assertFalse(b.after_touching(a))

        self.assertFalse(a.starts_before(b))
        self.assertFalse(b.starts_before(a))
        self.assertFalse(a.starts_after(b))
        self.assertFalse(b.starts_after(a))

        self.assertTrue(a.ends_before(b))
        self.assertFalse(b.ends_before(a))
        self.assertFalse(a.ends_after(b))
        self.assertTrue(b.ends_after(a))

        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

        self.assertFalse(a.contains(b))
        self.assertTrue(b.contains(a))

        self.assertTrue(a in b)
        self.assertFalse(b in a)

        self.assertFalse(start_before_key(a) < start_before_key(b))
        self.assertFalse(start_before_key(b) < start_before_key(a))

        with self.assertRaises(NotImplementedError):
            a < b
        with self.assertRaises(NotImplementedError):
            a > b
        with self.assertRaises(NotImplementedError):
            a <= b
        with self.assertRaises(NotImplementedError):
            a >= b

        overlap = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.INCLUSIVE, Bound.EXCLUSIVE),
        )
        self.assertEqual(a.overlapping_range(b), overlap)
        self.assertEqual(b.overlapping_range(a), overlap)

    def test_equality_ei_ii(self):
        """
        Comparisons on ranges with equal respective start and end (EI II).
        """
        # a = (x,y], b = [x,y]
        a = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.INCLUSIVE),
        )
        b = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )

        self.assertFalse(a.before_disjoint(b))
        self.assertFalse(b.before_disjoint(a))
        self.assertFalse(a.after_disjoint(b))
        self.assertFalse(b.after_disjoint(a))

        self.assertFalse(a.before_overlaps(b))
        self.assertTrue(b.before_overlaps(a))
        self.assertTrue(a.after_overlaps(b))
        self.assertFalse(b.after_overlaps(a))

        self.assertFalse(a.before_touching(b))
        self.assertFalse(b.before_touching(a))
        self.assertFalse(a.after_touching(b))
        self.assertFalse(b.after_touching(a))

        self.assertFalse(a.starts_before(b))
        self.assertTrue(b.starts_before(a))
        self.assertTrue(a.starts_after(b))
        self.assertFalse(b.starts_after(a))

        self.assertFalse(a.ends_before(b))
        self.assertFalse(b.ends_before(a))
        self.assertFalse(a.ends_after(b))
        self.assertFalse(b.ends_after(a))

        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

        self.assertFalse(a.contains(b))
        self.assertTrue(b.contains(a))

        self.assertTrue(a in b)
        self.assertFalse(b in a)

        self.assertFalse(start_before_key(a) < start_before_key(b))
        self.assertTrue(start_before_key(b) < start_before_key(a))

        with self.assertRaises(NotImplementedError):
            a < b
        with self.assertRaises(NotImplementedError):
            a > b
        with self.assertRaises(NotImplementedError):
            a <= b
        with self.assertRaises(NotImplementedError):
            a >= b

        overlap = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.EXCLUSIVE, Bound.INCLUSIVE),
        )
        self.assertEqual(a.overlapping_range(b), overlap)
        self.assertEqual(b.overlapping_range(a), overlap)

    def test_equality_ii_ii(self):
        """
        Comparisons on ranges with equal respective start and end (II II).
        """
        # a = [x,y], b = [x,y]
        a = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )
        b = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )

        self.assertFalse(a.before_disjoint(b))
        self.assertFalse(b.before_disjoint(a))
        self.assertFalse(a.after_disjoint(b))
        self.assertFalse(b.after_disjoint(a))

        self.assertFalse(a.before_overlaps(b))
        self.assertFalse(b.before_overlaps(a))
        self.assertFalse(a.after_overlaps(b))
        self.assertFalse(b.after_overlaps(a))

        self.assertFalse(a.before_touching(b))
        self.assertFalse(b.before_touching(a))
        self.assertFalse(a.after_touching(b))
        self.assertFalse(b.after_touching(a))

        self.assertFalse(a.starts_before(b))
        self.assertFalse(b.starts_before(a))
        self.assertFalse(a.starts_after(b))
        self.assertFalse(b.starts_after(a))

        self.assertFalse(a.ends_before(b))
        self.assertFalse(b.ends_before(a))
        self.assertFalse(a.ends_after(b))
        self.assertFalse(b.ends_after(a))

        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

        self.assertTrue(a.contains(b))
        self.assertTrue(b.contains(a))

        self.assertTrue(a in b)
        self.assertTrue(b in a)

        self.assertFalse(start_before_key(a) < start_before_key(b))
        self.assertFalse(start_before_key(b) < start_before_key(a))

        with self.assertRaises(NotImplementedError):
            a < b
        with self.assertRaises(NotImplementedError):
            a > b
        with self.assertRaises(NotImplementedError):
            a <= b
        with self.assertRaises(NotImplementedError):
            a >= b

        overlap = DatetimeRange(
            datetime(2012, 1, 1),
            datetime(2012, 1, 5),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )
        self.assertEqual(a.overlapping_range(b), overlap)
        self.assertEqual(b.overlapping_range(a), overlap)

    def test_contains(self):
        """
        Comparisons on ranges where one contains the other.

        Visualization of the test range used:

         [234]
        [12345]
        """
        smaller = DatetimeRange(datetime(2012, 1, 2), datetime(2012, 1, 4))
        bigger = DatetimeRange(datetime(2012, 1, 1), datetime(2012, 1, 5))

        self.assertFalse(smaller.before_disjoint(bigger))
        self.assertFalse(bigger.before_disjoint(smaller))
        self.assertFalse(smaller.after_disjoint(bigger))
        self.assertFalse(bigger.after_disjoint(smaller))

        self.assertFalse(smaller.before_overlaps(bigger))
        self.assertFalse(bigger.before_overlaps(smaller))
        self.assertFalse(smaller.after_overlaps(bigger))
        self.assertFalse(bigger.after_overlaps(smaller))

        self.assertFalse(smaller.before_touching(bigger))
        self.assertFalse(bigger.before_touching(smaller))
        self.assertFalse(smaller.after_touching(bigger))
        self.assertFalse(bigger.after_touching(smaller))

        self.assertFalse(smaller.starts_before(bigger))
        self.assertTrue(bigger.starts_before(smaller))
        self.assertTrue(smaller.starts_after(bigger))
        self.assertFalse(bigger.starts_after(smaller))

        self.assertTrue(smaller.ends_before(bigger))
        self.assertFalse(bigger.ends_before(smaller))
        self.assertFalse(smaller.ends_after(bigger))
        self.assertTrue(bigger.ends_after(smaller))

        self.assertTrue(smaller.overlaps(bigger))
        self.assertTrue(bigger.overlaps(smaller))

        self.assertFalse(smaller.contains(bigger))
        self.assertTrue(bigger.contains(smaller))

        self.assertTrue(smaller in bigger)
        self.assertFalse(bigger in smaller)

        self.assertFalse(start_before_key(smaller) < start_before_key(bigger))
        self.assertTrue(start_before_key(bigger) < start_before_key(smaller))

        with self.assertRaises(NotImplementedError):
            smaller < bigger
        with self.assertRaises(NotImplementedError):
            smaller > bigger
        with self.assertRaises(NotImplementedError):
            smaller <= bigger
        with self.assertRaises(NotImplementedError):
            smaller >= bigger

        overlap = DatetimeRange(datetime(2012, 1, 2), datetime(2012, 1, 4))
        self.assertEqual(smaller.intersection(bigger), overlap)
        self.assertEqual(bigger.intersection(smaller), overlap)

    # DatetimeRange to datetime comparisions

    def test_before_datetime(self):
        """
        Comparisons on a datetime range before a datetime.
        """
        dtr = DatetimeRange(datetime(2012, 1, 1), datetime(2012, 1, 2))
        dt = datetime(2012, 1, 3)

        self.assertTrue(dtr.before_disjoint(dt))
        self.assertFalse(dtr.after_disjoint(dt))

        self.assertFalse(dtr.contains(dt))
        self.assertFalse(dt in dtr)

    def test_before_touching_datetime_exclusive(self):
        """
        Comparisons on a datetime range start touching a datetime (E).
        """
        dtr = DatetimeRange(datetime(2012, 1, 1), datetime(2012, 1, 3), Bound.EXCLUSIVE)
        dt = datetime(2012, 1, 3)

        self.assertTrue(dtr.before_disjoint(dt))
        self.assertFalse(dtr.after_disjoint(dt))

        self.assertFalse(dtr.contains(dt))
        self.assertFalse(dt in dtr)

    def test_before_touching_datetime_inclusive(self):
        """
        Comparisons on a datetime range start touching a datetime (I).
        """
        dtr = DatetimeRange(datetime(2012, 1, 1), datetime(2012, 1, 3), Bound.INCLUSIVE)
        dt = datetime(2012, 1, 3)

        self.assertFalse(dtr.before_disjoint(dt))
        self.assertFalse(dtr.after_disjoint(dt))

        self.assertTrue(dtr.contains(dt))
        self.assertTrue(dt in dtr)

    def test_containing_datetime(self):
        """
        Comparisons on a datetime range which contains datetime.
        """
        dtr = DatetimeRange(datetime(2012, 1, 1), datetime(2012, 1, 5))
        dt = datetime(2012, 1, 3)

        self.assertFalse(dtr.before_disjoint(dt))
        self.assertFalse(dtr.after_disjoint(dt))

        self.assertTrue(dtr.contains(dt))
        self.assertTrue(dt in dtr)

    def test_after_touching_datetime_inclusive(self):
        """
        Comparisons on a datetime range end touching a datetime (I).
        """
        dtr = DatetimeRange(datetime(2012, 1, 3), datetime(2012, 1, 5), Bound.INCLUSIVE)
        dt = datetime(2012, 1, 3)

        self.assertFalse(dtr.before_disjoint(dt))
        self.assertFalse(dtr.after_disjoint(dt))

        self.assertTrue(dtr.contains(dt))
        self.assertTrue(dt in dtr)

    def test_after_touching_datetime_exclusive(self):
        """
        Comparisons on a datetime range end touching a datetime (E).
        """
        dtr = DatetimeRange(datetime(2012, 1, 3), datetime(2012, 1, 5), Bound.EXCLUSIVE)
        dt = datetime(2012, 1, 3)

        self.assertFalse(dtr.before_disjoint(dt))
        self.assertTrue(dtr.after_disjoint(dt))

        self.assertFalse(dtr.contains(dt))
        self.assertFalse(dt in dtr)

    def test_after_datetime(self):
        """
        Comparisons on a datetime range after a datetime.
        """
        dtr = DatetimeRange(datetime(2012, 1, 4), datetime(2012, 1, 5))
        dt = datetime(2012, 1, 3)

        self.assertFalse(dtr.before_disjoint(dt))
        self.assertTrue(dtr.after_disjoint(dt))

        self.assertFalse(dtr.contains(dt))
        self.assertFalse(dt in dtr)

    def test_relativedelta(self):
        dtr = DatetimeRange(datetime(2012, 1, 1), datetime(2013, 1, 1))
        dt = datetime(2012, 1, 1)
        dates = [
            datetime(2012, 1, 1),
            datetime(2012, 2, 1),
            datetime(2012, 3, 1),
            datetime(2012, 4, 1),
            datetime(2012, 5, 1),
            datetime(2012, 6, 1),
            datetime(2012, 7, 1),
            datetime(2012, 8, 1),
            datetime(2012, 9, 1),
            datetime(2012, 10, 1),
            datetime(2012, 11, 1),
            datetime(2012, 12, 1),
            datetime(2013, 1, 1),
        ]
        year_dates = [datetime(2012, 1, 1), datetime(2013, 1, 1)]
        ranges = [
            DatetimeRange(s, e, range_bounds) for s, e in zip(dates[0:-1], dates[1::])
        ]
        year_ranges = [
            DatetimeRange(s, e, range_bounds)
            for s, e in zip(year_dates[0:-1], year_dates[1::])
        ]

        self.assertEqual(list(dtr.dates(relativedelta(0))), [dt])
        self.assertEqual(list(dtr.dates(relativedelta(months=1))), dates)
        self.assertEqual(list(dtr.dates(relativedelta(years=1))), year_dates)

        self.assertEqual(
            list(dtr.ranges(relativedelta(0))), [DatetimeRange(dt, dt, range_bounds)]
        )  # noqa: E501
        self.assertEqual(list(dtr.ranges(relativedelta(months=1))), ranges)
        self.assertEqual(
            list(dtr.ranges(relativedelta(years=1))), year_ranges
        )  # noqa: E501

        with self.assertRaises(ValueError):
            next(dtr.dates(relativedelta(months=-1)))
        with self.assertRaises(ValueError):
            next(dtr.ranges(relativedelta(months=-1)))

    def test_sorted(self):
        """
        Sorting when used without a key or cmp function uses __lt__.
        Ensure that sorting works as expected.
        """
        dtrs = [
            DatetimeRange(
                datetime(2015, 1, 1),
                datetime(2015, 3, 1),
                (Bound.INCLUSIVE, Bound.EXCLUSIVE),
            ),
            DatetimeRange(
                datetime(2015, 1, 1),
                datetime(2015, 6, 1),
                (Bound.INCLUSIVE, Bound.EXCLUSIVE),
            ),
            DatetimeRange(
                datetime(2015, 3, 1),
                datetime(2015, 6, 1),
                (Bound.INCLUSIVE, Bound.EXCLUSIVE),
            ),
        ]

        with self.assertRaises(NotImplementedError):
            sorted(dtrs[::1])
        with self.assertRaises(NotImplementedError):
            sorted(dtrs[::-1])

        self.assertEqual(sorted(dtrs[::1], key=start_before_key), dtrs)
        # Indices 0 and 1 treated as equal since they have the same start.
        self.assertEqual(
            sorted(dtrs[::-1], key=start_before_key),
            dtrs[1::-1] + dtrs[2:3],  # Indices: 1, 0, 2
        )

    def test_infinite_end(self):
        dtr = DatetimeRange(datetime(2013, 1, 1), None)

        self.assertEqual(dtr.start, datetime(2013, 1, 1))
        self.assertEqual(dtr.end, POS_INF_DATETIME)
        self.assertEqual(dtr.end_included, False)
        self.assertEqual(dtr.end_infinite, True)
        self.assertEqual(dtr.infinite_endpoints, True)

        with self.assertRaises(ValueError):
            dtr.end_included = True
        with self.assertRaises(ValueError):
            next(dtr.dates(timedelta(hours=1)))
        with self.assertRaises(ValueError):
            next(dtr.ranges(timedelta(hours=1)))

        dtr.end_infinite = False
        self.assertEqual(dtr.end, POS_INF_DATETIME)
        self.assertEqual(dtr.end_included, False)
        self.assertEqual(dtr.end_infinite, False)

        bounds = [
            Bound.INCLUSIVE,
            Bound.EXCLUSIVE,
            (Bound.INCLUSIVE, Bound.EXCLUSIVE),
            (Bound.EXCLUSIVE, Bound.INCLUSIVE),
        ]
        for bound in bounds:
            dtr = DatetimeRange(datetime(2013, 1, 1), None, bound)

            self.assertEqual(dtr.start, datetime(2013, 1, 1))
            self.assertEqual(dtr.end, POS_INF_DATETIME)
            self.assertEqual(dtr.end_included, False)
            self.assertEqual(dtr.end_infinite, True)
            self.assertEqual(dtr.infinite_endpoints, True)

    def test_infinite_set_end(self):
        dt = datetime(2013, 1, 1)
        dtr = DatetimeRange(dt, dt)

        self.assertEqual(dtr.end, dt)
        self.assertEqual(dtr.end_included, True)
        self.assertEqual(dtr.end_infinite, False)

        dtr.end = None  # Treated as Inf

        self.assertEqual(dtr.end, POS_INF_DATETIME)
        self.assertEqual(dtr.end_included, False)
        self.assertEqual(dtr.end_infinite, True)

        dtr.end = dt

        self.assertEqual(dtr.end, dt)
        self.assertEqual(dtr.end_included, False)
        self.assertEqual(dtr.end_infinite, False)

        dtr.end = POS_INF_DATETIME

        self.assertEqual(dtr.end, POS_INF_DATETIME)
        self.assertEqual(dtr.end_included, False)
        self.assertEqual(dtr.end_infinite, True)

    def test_containing_infinite_end(self):
        """
        Creation of dateime range via containing.

        Visualization of the test range used:

          (2,Inf)
        (01)
        """
        test = [
            DatetimeRange(datetime(2013, 1, 1, 2), None, Bound.EXCLUSIVE),
            DatetimeRange(
                datetime(2013, 1, 1, 0), datetime(2013, 1, 1, 1), Bound.EXCLUSIVE
            ),
        ]
        expected = DatetimeRange(
            datetime(2013, 1, 1, 0), None, (Bound.EXCLUSIVE, Bound.EXCLUSIVE)
        )

        result = DatetimeRange.containing(test)
        self.assertEqual(result, expected)

    def test_compare_ranges(self):
        dates = [
            datetime(2013, 1, 1),
            datetime(2014, 1, 1),
            datetime(2015, 1, 1),
            datetime(2016, 1, 1),
        ]
        test_data = [
            DatetimeRange(dates[0], dates[2]),
            DatetimeRange(dates[0], dates[3]),
            DatetimeRange(dates[1], dates[2]),
            DatetimeRange(dates[1], dates[3]),
            (DatetimeRange(dates[0], dates[3]), 0),
            (DatetimeRange(dates[1], dates[3]), 0),
            ("invalid", DatetimeRange(dates[0], dates[2])),
        ]

        self.assertEqual(cmp_ranges(test_data[0], test_data[3]), -1)
        self.assertEqual(cmp_ranges(test_data[0], test_data[2]), -1)
        self.assertEqual(cmp_ranges(test_data[1], test_data[2]), -1)
        self.assertEqual(cmp_ranges(test_data[2], test_data[1]), 1)
        self.assertEqual(cmp_ranges(test_data[2], test_data[0]), 1)
        self.assertEqual(cmp_ranges(test_data[3], test_data[0]), 1)
        self.assertEqual(cmp_ranges(test_data[0], test_data[1]), -1)
        self.assertEqual(cmp_ranges(test_data[0], test_data[0]), 0)
        self.assertEqual(cmp_ranges(test_data[1], test_data[0]), 1)
        self.assertEqual(cmp_ranges(test_data[4], test_data[5]), -1)
        self.assertEqual(cmp_ranges(test_data[5], test_data[5]), 0)
        self.assertEqual(cmp_ranges(test_data[5], test_data[4]), 1)
        self.assertRaises(TypeError, cmp_ranges, test_data[0], test_data[4])
        self.assertRaises(TypeError, cmp_ranges, test_data[6], test_data[6])

    def test_effective_ranges(self):
        dates = [datetime(2013, 1, 1), datetime(2014, 1, 1), datetime(2015, 1, 1)]

        bounds = (Bound.INCLUSIVE, Bound.EXCLUSIVE)

        expected = [
            DatetimeRange(dates[0], dates[1], bounds=bounds),
            DatetimeRange(dates[1], dates[2], bounds=bounds),
            DatetimeRange(dates[2], datetime.max, bounds=bounds),
        ]

        self.assertEqual(list(DatetimeRange.effective_ranges(dates)), expected)

    def test_hash(self):
        """
        Make sure that two equal date time ranges hash to the same value.
        Important for working with datetime ranges within dictionaries.
        """
        a = DatetimeRange(
            datetime(2013, 1, 1),
            datetime(2014, 1, 1),
            (Bound.INCLUSIVE, Bound.EXCLUSIVE),
        )
        b = DatetimeRange(
            datetime(2013, 1, 1),
            datetime(2014, 1, 1),
            (Bound.INCLUSIVE, Bound.EXCLUSIVE),
        )
        self.assertEqual(hash(a), hash(b))


class TestPeriodEndingAsRange(unittest.TestCase):
    def test_ambiguous(self):
        wpg = pytz.timezone("America/Winnipeg")
        bounds = (Bound.INCLUSIVE, Bound.EXCLUSIVE)

        self.assertEqual(
            period_ending_as_range(
                localize(datetime(2013, 11, 3, 2), wpg), timedelta(hours=1)
            ),
            DatetimeRange(
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=False),
                localize(datetime(2013, 11, 3, 2), wpg),
                bounds,
            ),
        )
        self.assertEqual(
            period_ending_as_range(
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=False),
                timedelta(hours=1),
            ),
            DatetimeRange(
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=True),
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=False),
                bounds,
            ),
        )
        self.assertEqual(
            period_ending_as_range(
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=True), timedelta(hours=1)
            ),
            DatetimeRange(
                localize(datetime(2013, 11, 3, 0), wpg),
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=True),
                bounds,
            ),
        )

    def test_non_existent(self):
        wpg = pytz.timezone("America/Winnipeg")
        bounds = (Bound.INCLUSIVE, Bound.EXCLUSIVE)

        self.assertEqual(
            period_ending_as_range(
                localize(datetime(2013, 3, 10, 3), wpg), timedelta(hours=1)
            ),
            DatetimeRange(
                localize(datetime(2013, 3, 10, 1), wpg),
                localize(datetime(2013, 3, 10, 3), wpg),
                bounds,
            ),
        )


class TestPeriodBeginningAsRange(unittest.TestCase):
    def test_ambiguous(self):
        wpg = pytz.timezone("America/Winnipeg")
        bounds = (Bound.INCLUSIVE, Bound.EXCLUSIVE)

        self.assertEqual(
            period_beginning_as_range(
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=False),
                timedelta(hours=1),
            ),
            DatetimeRange(
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=False),
                localize(datetime(2013, 11, 3, 2), wpg),
                bounds,
            ),
        )
        self.assertEqual(
            period_beginning_as_range(
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=True), timedelta(hours=1)
            ),
            DatetimeRange(
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=True),
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=False),
                bounds,
            ),
        )
        self.assertEqual(
            period_beginning_as_range(
                localize(datetime(2013, 11, 3, 0), wpg), timedelta(hours=1)
            ),
            DatetimeRange(
                localize(datetime(2013, 11, 3, 0), wpg),
                localize(datetime(2013, 11, 3, 1), wpg, is_dst=True),
                bounds,
            ),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
