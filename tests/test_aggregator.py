import unittest
from datetime import datetime, timedelta

from inveniautils.aggregator import (
    TimeSeriesAggregate,
    extend_date_range,
    group_release_dates,
)
from inveniautils.dates import localize, utc
from inveniautils.datetime_range import Bound, DatetimeRange, period_ending_as_range

import pytz


def all_values(value_key):
    def aggregator(identifier, rows):
        result = dict(identifier)
        result[value_key] = [r[value_key] for r in rows if r[value_key] is not None]
        return result

    return aggregator


class TestTimeSeriesAggregate(unittest.TestCase):
    def test_hourly(self):
        period = timedelta(hours=1)
        dates = [
            localize(datetime(2016, 1, 1, 12, 20), utc),
            localize(datetime(2016, 1, 1, 12, 50), utc),
            localize(datetime(2016, 1, 1, 13, 20), utc),
            localize(datetime(2016, 1, 1, 13, 50), utc),
            localize(datetime(2016, 1, 1, 13, 0), utc),
            localize(datetime(2016, 1, 1, 14, 0), utc),
        ]
        dtrs = [DatetimeRange.containing(dt) for dt in dates]
        exp_dtr = [period_ending_as_range(dt, period) for dt in dates]
        test = [
            {"dt": dtrs[0], "rd": dates[1], "n": "a", "v": 0.011},
            {"dt": dtrs[0], "rd": dates[1], "n": "b", "v": 0.012},
            {"dt": dtrs[0], "rd": dates[2], "n": "b", "v": 0.022},
            {"dt": dtrs[0], "rd": dates[3], "n": "a", "v": 0.031},
            {"dt": dtrs[1], "rd": dates[2], "n": "b", "v": 0.122},
            {"dt": dtrs[1], "rd": dates[2], "n": "a", "v": 0.121},
            {"dt": dtrs[1], "rd": dates[3], "n": "a", "v": 0.131},
            {"dt": dtrs[2], "rd": dates[3], "n": "a", "v": 0.231},
        ]  # Ordering (dt, rd)
        expected = [
            {"dtr": exp_dtr[4], "rd": dates[1], "n": "a", "v": [0.011], "tag": None},
            {
                "dtr": exp_dtr[4],
                "rd": dates[2],
                "n": "a",
                "v": [0.011, 0.121],
                "tag": None,
            },
            {
                "dtr": exp_dtr[4],
                "rd": dates[3],
                "n": "a",
                "v": [0.031, 0.131],
                "tag": None,
            },
            {"dtr": exp_dtr[4], "rd": dates[1], "n": "b", "v": [0.012], "tag": None},
            {
                "dtr": exp_dtr[4],
                "rd": dates[2],
                "n": "b",
                "v": [0.022, 0.122],
                "tag": None,
            },
            {"dtr": exp_dtr[5], "rd": dates[3], "n": "a", "v": [0.231], "tag": None},
        ]

        hourly = TimeSeriesAggregate(
            primary_keys=["dt", "rd", "n"],
            group_by=["dt", "n"],
            target_key="dt",
            release_date_key="rd",
            aggregator=all_values("v"),
            period=period,
            output_target_key="dtr",
        )
        result = hourly(test)

        self.assertEqual(list(result), list(expected))

    def test_marketwide(self):
        # Same dataset as `test_hourly` test
        dates = [
            datetime(2016, 1, 1, 12, 20),
            datetime(2016, 1, 1, 12, 50),
            datetime(2016, 1, 1, 13, 20),
            datetime(2016, 1, 1, 13, 50),
            datetime(2016, 1, 1, 13, 0),
            datetime(2016, 1, 1, 14, 0),
        ]
        test = [
            {"dt": dates[0], "rd": dates[1], "n": "a", "v": 0.011},
            {"dt": dates[0], "rd": dates[1], "n": "b", "v": 0.012},
            {"dt": dates[0], "rd": dates[2], "n": "b", "v": 0.022},
            {"dt": dates[0], "rd": dates[3], "n": "a", "v": 0.031},
            {"dt": dates[1], "rd": dates[2], "n": "b", "v": 0.122},
            {"dt": dates[1], "rd": dates[2], "n": "a", "v": 0.121},
            {"dt": dates[1], "rd": dates[3], "n": "a", "v": 0.131},
            {"dt": dates[2], "rd": dates[3], "n": "a", "v": 0.231},
        ]  # Ordering (dt, rd)
        expected = [
            {"dt": dates[0], "rd": dates[1], "v": [0.011, 0.012], "tag": None},
            {"dt": dates[0], "rd": dates[2], "v": [0.011, 0.022], "tag": None},
            {"dt": dates[0], "rd": dates[3], "v": [0.031, 0.022], "tag": None},
            {"dt": dates[1], "rd": dates[2], "v": [0.122, 0.121], "tag": None},
            {"dt": dates[1], "rd": dates[3], "v": [0.122, 0.131], "tag": None},
            {"dt": dates[2], "rd": dates[3], "v": [0.231], "tag": None},
        ]

        market = TimeSeriesAggregate(
            primary_keys=["dt", "rd", "n"],
            group_by=["dt"],
            target_key="dt",
            release_date_key="rd",
            aggregator=all_values("v"),
            period=None,
        )
        result = market(test)

        self.assertEqual(list(result), list(expected))

    def test_ignore(self):
        """
        Check that having the aggregator return None throws the result
        away.
        """
        dates = [datetime(2016, 1, 1, 12, 20), datetime(2016, 1, 1, 12, 50)]
        test = [
            {"dt": dates[0], "rd": dates[1], "n": "a", "v": 0.011}
        ]  # Ordering (dt, rd)
        expected = []

        def ignore(identifier, rows):
            return None

        market = TimeSeriesAggregate(
            primary_keys=["dt", "rd", "n"],
            group_by=["dt", "n"],
            target_key="dt",
            release_date_key="rd",
            aggregator=ignore,
            period=None,
        )
        result = market(test)

        self.assertEqual(list(result), list(expected))

    def test_relevancy_check(self):
        """
        Mostly realistic test taken from MISO 5-minute data which
        """
        period = timedelta(hours=1)
        dates = [
            localize(datetime(2015, 3, 3, 0, 5), utc),
            localize(datetime(2015, 3, 3, 0, 10), utc),
            localize(datetime(2015, 3, 3, 1), utc),
        ]
        rd = [datetime(2015, 3, 3, 5, 10, 6), datetime(2015, 3, 3, 5, 15)]
        dtrs = [DatetimeRange.containing(dt) for dt in dates]
        exp_dtrs = [period_ending_as_range(dt, period) for dt in dates]
        test = [
            {"dt": dtrs[0], "n": "ERCO", "rd": rd[0], "lmp": 21.49},
            {"dt": dtrs[0], "n": "FPLL", "rd": rd[0], "lmp": 22.47},
            {"dt": dtrs[1], "n": "ERCO", "rd": rd[1], "lmp": 22.77},
            {"dt": dtrs[1], "n": "FPLL", "rd": rd[1], "lmp": 23.89},
        ]
        expected = [
            {"dtr": exp_dtrs[2], "n": "ERCO", "rd": rd[0], "lmp": [21.49], "tag": None},
            {
                "dtr": exp_dtrs[2],
                "n": "ERCO",
                "rd": rd[1],
                "lmp": [21.49, 22.77],
                "tag": None,
            },
            {"dtr": exp_dtrs[2], "n": "FPLL", "rd": rd[0], "lmp": [22.47], "tag": None},
            {
                "dtr": exp_dtrs[2],
                "n": "FPLL",
                "rd": rd[1],
                "lmp": [22.47, 23.89],
                "tag": None,
            },
        ]

        hourly = TimeSeriesAggregate(
            primary_keys=["dt", "n", "rd"],
            group_by=["dt", "n"],
            target_key="dt",
            release_date_key="rd",
            aggregator=all_values("lmp"),
            period=period,
            output_target_key="dtr",
        )
        result = hourly(test, relevancy_check=1)
        self.assertEqual(list(result), list(expected))

    def test_reducer(self):
        """
        When release dates differ we get additional rows. In some cases the
        release dates are "close enough" that we should treat them as the same.
        Based off of real data from CAISO real-time.
        """
        central = pytz.timezone("US/Central")
        period = timedelta(hours=1)
        test = [
            {
                "target_date": DatetimeRange.containing(
                    localize(datetime(2016, 9, 1, 0, 15), central)
                ),
                "node_name": "AEEC",
                "release_date": localize(datetime(2016, 9, 6, 15, 1, 15), utc),
                "lmp": 20.97,
            },
            {
                "target_date": DatetimeRange.containing(
                    localize(datetime(2016, 9, 1, 0, 30), central)
                ),
                "node_name": "AEEC",
                "release_date": localize(datetime(2016, 9, 6, 15, 1, 16), utc),
                "lmp": 20.8,
            },
            {
                "target_date": DatetimeRange.containing(
                    localize(datetime(2016, 9, 1, 0, 45), central)
                ),
                "node_name": "AEEC",
                "release_date": localize(datetime(2016, 9, 6, 15, 1, 17), utc),
                "lmp": 20.21,
            },
            {
                "target_date": DatetimeRange.containing(
                    localize(datetime(2016, 9, 1, 1, 0), central)
                ),
                "node_name": "AEEC",
                "release_date": localize(datetime(2016, 9, 6, 15, 1, 17), utc),
                "lmp": 19.87,
            },
        ]
        expected = [
            {
                "target_range": period_ending_as_range(
                    localize(datetime(2016, 9, 1, 1, 0), central), period
                ),
                "node_name": "AEEC",
                "release_date": localize(datetime(2016, 9, 6, 15, 1, 17), utc),
                "lmp": [20.97, 20.8, 20.21, 19.87],
                "tag": None,
            }
        ]

        hourly = TimeSeriesAggregate(
            primary_keys=["target_date", "node_name", "release_date"],
            group_by=["target_date", "node_name"],
            target_key="target_date",
            release_date_key="release_date",
            aggregator=all_values("lmp"),
            period=period,
            output_target_key="target_range",
            # release_period=timedelta(minutes=1),
            release_dates_reducer=group_release_dates(timedelta(minutes=1)),
        )
        result = hourly(test)
        self.assertEqual(list(result), list(expected))

    def test_reducer_complicated(self):
        """
        Loosely based off of PJM real-time instant bus data.
        """
        period = timedelta(hours=1)
        test = [
            {
                "dt": DatetimeRange.containing(
                    localize(datetime(2016, 5, 1, 4, 5), utc)
                ),
                "n": 1348265112,
                "rd": datetime(2016, 5, 1, 4, 10, 3),
                "v": 20,
            },
            {
                "dt": DatetimeRange.containing(
                    localize(datetime(2016, 5, 1, 4, 10), utc)
                ),
                "n": 1348265112,
                "rd": datetime(2016, 5, 5, 12),  # Very late data
                "v": 30,
            },
            {
                "dt": DatetimeRange.containing(
                    localize(datetime(2016, 5, 1, 4, 15), utc)
                ),
                "n": 1348265112,
                "rd": datetime(2016, 5, 1, 4, 20, 7),
                "v": 40,
            },
            {
                "dt": DatetimeRange.containing(
                    localize(datetime(2016, 5, 1, 4, 15), utc)
                ),
                "n": 1348265112,
                "rd": datetime(2016, 5, 5, 12),  # Very late data
                "v": 50,
            },
            {
                "dt": DatetimeRange.containing(localize(datetime(2016, 5, 1, 5), utc)),
                "n": 1348265112,
                "rd": datetime(2016, 5, 1, 5, 5, 2),
                "v": 60,
            },
        ]
        range_he = lambda dt: period_ending_as_range(dt, period)
        expected = [
            {
                "dtr": range_he(localize(datetime(2016, 5, 1, 5), utc)),
                "n": 1348265112,
                "rd": datetime(2016, 5, 1, 5, 5, 2),
                "v": [20, 40, 60],
                "tag": None,
            },
            {
                "dtr": range_he(localize(datetime(2016, 5, 1, 5), utc)),
                "n": 1348265112,
                "rd": datetime(2016, 5, 5, 12),
                "v": [20, 30, 50, 60],
                "tag": None,
            },
        ]

        hourly = TimeSeriesAggregate(
            primary_keys=["dt", "n", "rd"],
            group_by=["dt", "n"],
            target_key="dt",
            release_date_key="rd",
            aggregator=all_values("v"),
            period=period,
            output_target_key="dtr",
            release_dates_reducer=group_release_dates(timedelta(hours=1)),
        )
        result = hourly(test)
        self.assertEqual(list(result), list(expected))


class TestExtendDateRange(unittest.TestCase):
    def test_hourly_basic(self):
        test = DatetimeRange(datetime(2015, 1, 1, 6, 5), datetime(2015, 1, 1, 7, 0))
        expected = DatetimeRange(
            datetime(2015, 1, 1, 6, 0),
            datetime(2015, 1, 1, 7, 0),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )
        self.assertEqual(extend_date_range(test, timedelta(hours=1)), expected)

    def test_none(self):
        test = None
        expected = None
        self.assertEqual(extend_date_range(test, timedelta(hours=1)), expected)

    def test_hourly_over_hour(self):
        test = DatetimeRange(datetime(2015, 1, 1, 5, 55), datetime(2015, 1, 1, 6, 5))
        expected = DatetimeRange(
            datetime(2015, 1, 1, 5, 0),
            datetime(2015, 1, 1, 6, 0),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )
        self.assertEqual(extend_date_range(test, timedelta(hours=1)), expected)

    def test_hourly_not_over_hour(self):
        test = DatetimeRange(datetime(2015, 1, 1, 6, 5), datetime(2015, 1, 1, 6, 55))
        expected = DatetimeRange(
            datetime(2015, 1, 1, 6, 0),
            datetime(2015, 1, 1, 6, 0),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )
        self.assertEqual(extend_date_range(test, timedelta(hours=1)), expected)

    def test_hourly_bounds_exclusive(self):
        test = DatetimeRange(
            datetime(2016, 9, 1, 2),
            datetime(2016, 9, 1, 3),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )
        expected = DatetimeRange(
            datetime(2016, 9, 1, 2),
            datetime(2016, 9, 1, 3),
            (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
        )
        self.assertEqual(extend_date_range(test, timedelta(hours=1)), expected)

    def test_hourly_bounds_inclusive(self):
        test = DatetimeRange(
            datetime(2016, 9, 1, 2),
            datetime(2016, 9, 1, 3),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )
        expected = DatetimeRange(
            datetime(2016, 9, 1, 1),
            datetime(2016, 9, 1, 3),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )
        self.assertEqual(extend_date_range(test, timedelta(hours=1)), expected)

    def test_bound_specification(self):
        test = DatetimeRange(
            datetime(2016, 9, 1, 2),
            datetime(2016, 9, 1, 3),
            (Bound.INCLUSIVE, Bound.INCLUSIVE),
        )
        expected = DatetimeRange(
            datetime(2016, 9, 1, 1),
            datetime(2016, 9, 1, 3),
            (Bound.EXCLUSIVE, Bound.INCLUSIVE),
        )
        self.assertEqual(
            extend_date_range(
                test, timedelta(hours=1), bounds=(Bound.EXCLUSIVE, Bound.INCLUSIVE)
            ),
            expected,
        )
