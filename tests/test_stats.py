import logging
import unittest
from datetime import datetime, timedelta

from inveniautils.dates import localize
from inveniautils.datetime_range import Bound, DatetimeRange
from inveniautils.stats import (
    best_delta,
    instance_analysis,
    range_analysis,
    range_pair_analysis,
    release_estimations,
)

import pytz


class TestInstanceAnaylsis(unittest.TestCase):
    def test_basic(self):
        target_dates = [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
            datetime(2014, 1, 1),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2014, 1, 1)
        expected_step = timedelta(days=365)

        start, step, end = instance_analysis(target_dates)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_empty(self):
        target_dates = []
        expected_start = None
        expected_end = None
        expected_step = timedelta(0)

        start, step, end = instance_analysis(target_dates)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_single(self):
        target_dates = [
            datetime(2010, 1, 1),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2010, 1, 1)
        expected_step = timedelta(0)

        start, step, end = instance_analysis(target_dates)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_variable_step(self):
        target_dates = [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2013, 1, 1),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2013, 1, 1)
        expected_step = None

        start, step, end = instance_analysis(target_dates)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_missing(self):
        target_dates = [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 1, 1),
            # Missing 2013
            datetime(2014, 1, 1),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2014, 1, 1)
        expected_step = timedelta(days=365)

        start, step, end = instance_analysis(target_dates)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)


class TestRangeAnalysis(unittest.TestCase):
    def test_basic(self):
        ranges = [
            DatetimeRange(datetime(2010, 1, 1), datetime(2011, 1, 1)),
            DatetimeRange(datetime(2011, 1, 1), datetime(2012, 1, 1)),
            DatetimeRange(datetime(2012, 1, 1), datetime(2013, 1, 1)),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2013, 1, 1)
        expected_step = timedelta(days=365)

        start, step, end = range_analysis(ranges)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_empty(self):
        ranges = []
        expected_start = None
        expected_end = None
        expected_step = timedelta(0)

        start, step, end = range_analysis(ranges)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_bounds(self):
        ranges = [
            DatetimeRange(
                datetime(2010, 1, 1),
                datetime(2011, 1, 1),
                (Bound.EXCLUSIVE, Bound.INCLUSIVE),
            ),
            DatetimeRange(
                datetime(2010, 1, 1),
                datetime(2011, 1, 1),
                (Bound.EXCLUSIVE, Bound.EXCLUSIVE),
            ),
            DatetimeRange(
                datetime(2012, 1, 1),
                datetime(2013, 1, 1),
                (Bound.INCLUSIVE, Bound.INCLUSIVE),
            ),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2013, 1, 1)
        expected_step = timedelta(days=365)

        start, step, end = range_analysis(ranges)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_single(self):
        ranges = [
            DatetimeRange(datetime(2010, 1, 1), datetime(2011, 1, 1)),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2011, 1, 1)
        expected_step = timedelta(days=365)

        start, step, end = range_analysis(ranges)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_variable_step(self):
        ranges = [
            DatetimeRange(datetime(2010, 1, 1), datetime(2010, 2, 1)),
            DatetimeRange(datetime(2010, 1, 1), datetime(2010, 3, 1)),
            DatetimeRange(datetime(2010, 1, 1), datetime(2010, 4, 1)),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2010, 4, 1)
        expected_step = None

        start, step, end = range_analysis(ranges)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_infinite_range(self):
        ranges = [
            DatetimeRange(datetime(2010, 1, 1), None),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = None
        expected_step = None

        start, step, end = range_analysis(ranges)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_mixed_finite_and_infinite(self):
        ranges = [
            DatetimeRange(datetime(2010, 1, 1), datetime(2010, 1, 2)),
            DatetimeRange(datetime(2010, 1, 2), datetime(2010, 1, 3)),
            DatetimeRange(datetime(2010, 1, 3), None),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = None
        expected_step = timedelta(days=1)  # Maybe somewhat unexpected?

        start, step, end = range_analysis(ranges)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)


class TestRangePairAnalysis(unittest.TestCase):
    def test_basic(self):
        ranges = [
            (datetime(2010, 1, 1), datetime(2011, 1, 1)),
            (datetime(2011, 1, 1), datetime(2012, 1, 1)),
            (datetime(2012, 1, 1), datetime(2013, 1, 1)),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2013, 1, 1)
        expected_step = timedelta(days=365)

        start, step, end = range_pair_analysis(ranges)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_single(self):
        ranges = [
            (datetime(2010, 1, 1), datetime(2011, 1, 1)),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2011, 1, 1)
        expected_step = timedelta(days=365)

        start, step, end = range_pair_analysis(ranges)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)

    def test_variable_step(self):
        ranges = [
            (datetime(2010, 1, 1), datetime(2010, 2, 1)),
            (datetime(2010, 1, 1), datetime(2010, 3, 1)),
            (datetime(2010, 1, 1), datetime(2010, 4, 1)),
        ]
        expected_start = datetime(2010, 1, 1)
        expected_end = datetime(2010, 4, 1)
        expected_step = None

        start, step, end = range_pair_analysis(ranges)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)
        self.assertEqual(step, expected_step)


class TestBestDelta(unittest.TestCase):
    def test_basic(self):
        sample = [
            timedelta(minutes=5),
            timedelta(minutes=10),
            timedelta(minutes=5),
        ]
        self.assertEqual(best_delta(sample), timedelta(minutes=5))

    def test_ambiguous(self):
        sample = [timedelta(minutes=i) for i in range(0, 60, 5)]

        # Just takes the first delta from the sample.
        # This is different than Python 2.7, as Dictionaries are now ordered.
        self.assertEqual(best_delta(sample), timedelta(minutes=0))

    def test_interval(self):
        sample = [
            timedelta(minutes=55),
            timedelta(minutes=59),
            timedelta(minutes=120),
        ]

        self.assertEqual(
            best_delta(sample, timedelta(hours=1)),
            timedelta(hours=1),
        )

    def test_real(self):
        sample = [
            timedelta(hours=1, minutes=57),
            timedelta(hours=3, minutes=35),
            timedelta(hours=4, minutes=58),
            timedelta(hours=4, minutes=49),
            timedelta(hours=5, minutes=55),
            timedelta(hours=5, minutes=59),
            timedelta(hours=6, minutes=35),
        ]

        self.assertEqual(
            best_delta(sample, timedelta(hours=1)),
            timedelta(hours=5),
        )

        self.assertEqual(
            best_delta(sample, timedelta(hours=1), tolerance=1.0),
            timedelta(hours=5),
        )

        self.assertEqual(
            best_delta(sample, timedelta(hours=1), tolerance=0.5),
            timedelta(hours=4),
        )

    def test_real_neg(self):
        sample = [
            -timedelta(hours=1, minutes=57),
            -timedelta(hours=3, minutes=35),
            -timedelta(hours=4, minutes=58),
            -timedelta(hours=4, minutes=49),
            -timedelta(hours=5, minutes=55),
            -timedelta(hours=5, minutes=59),
            -timedelta(hours=6, minutes=35),
        ]

        self.assertEqual(
            best_delta(sample, timedelta(hours=1)),
            -timedelta(hours=5),
        )

        self.assertEqual(
            best_delta(sample, timedelta(hours=1), tolerance=1.0),
            -timedelta(hours=5),
        )

        self.assertEqual(
            best_delta(sample, timedelta(hours=1), tolerance=0.5),
            -timedelta(hours=4),
        )


class TestReleaseEstimates(unittest.TestCase):
    def test_pjm_da_shadow_prices(self):
        eastern = pytz.timezone("US/Eastern")
        modified_dates = [
            localize(datetime(2016, 1, 4, 16, 54, 24), eastern),
            localize(datetime(2016, 1, 18, 16, 18, 41), eastern),
            localize(datetime(2016, 1, 19, 16, 18, 49), eastern),
            localize(datetime(2016, 1, 20, 16, 18, 31), eastern),
        ]
        content_end_dates = [
            localize(datetime(2016, 1, 1), eastern),
            localize(datetime(2016, 1, 20), eastern),
            localize(datetime(2016, 1, 21), eastern),
            localize(datetime(2016, 1, 22), eastern),
        ]
        expected_publish_interval = timedelta(days=1)
        expected_publish_offset = timedelta(hours=16, minutes=20)
        expected_content_interval = timedelta(days=1)
        expected_content_offset = timedelta(days=2)

        r = release_estimations(
            modified_dates, content_end_dates, timedelta(minutes=5),
        )
        publish_interval, publish_offset, content_interval, content_offset = r

        self.assertEqual(publish_interval, expected_publish_interval)
        self.assertEqual(publish_offset, expected_publish_offset)
        self.assertEqual(content_interval, expected_content_interval)
        self.assertEqual(content_offset, expected_content_offset)

    def test_pjm_load_forecast_http(self):
        eastern = pytz.timezone("US/Eastern")
        modified_dates = [
            localize(datetime(2016, 5, 14, 22, 20, 1), eastern),
            localize(datetime(2016, 5, 14, 22, 50, 1), eastern),
            localize(datetime(2016, 5, 14, 23, 20, 1), eastern),
            localize(datetime(2016, 5, 15, 00, 20, 1), eastern),
            localize(datetime(2016, 5, 15, 00, 50, 1), eastern),
            localize(datetime(2016, 5, 15, 1, 20, 1), eastern),
        ]
        content_end_dates = [
            localize(datetime(2016, 5, 21), eastern),
            localize(datetime(2016, 5, 21), eastern),
            localize(datetime(2016, 5, 21), eastern),
            localize(datetime(2016, 5, 22), eastern),
            localize(datetime(2016, 5, 22), eastern),
            localize(datetime(2016, 5, 22), eastern),
        ]
        expected = (
            timedelta(minutes=30),
            timedelta(minutes=20),
            timedelta(days=1),
            timedelta(days=7),  # Would be 7 days, 1 hour over fall DST
        )
        result = release_estimations(
            modified_dates, content_end_dates, timedelta(minutes=5),
        )
        self.assertEqual(result, expected)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
