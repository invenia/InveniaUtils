import logging
import unittest
from datetime import datetime, timedelta

from inveniautils.dates import (
    GUESS_DST, datetime_extract, estimate_content_end, estimate_latest_release,
    format_to_regex, localize, round_datetime, round_timedelta, split, contains,
    estimate_latest, localize_hour_ending, localize_period_ending,
    timezone_transitions
)

from inveniautils.dates import timezone as timezone_util

from dateutil.parser import parse as datetime_parser
from dateutil.relativedelta import relativedelta

from pytz import timezone, utc
from pytz.exceptions import NonExistentTimeError, AmbiguousTimeError

wpg = timezone('America/Winnipeg')


class TestLocalize(unittest.TestCase):
    def test_basic(self):
        dt = datetime(2015, 1, 1, 0)  # CST
        expected = wpg.localize(dt)

        self.assertEqual(localize(dt, wpg), expected)
        self.assertEqual(localize(dt, wpg, is_dst=None), expected)
        self.assertEqual(localize(dt, wpg, is_dst=GUESS_DST), expected)
        self.assertEqual(localize(dt, wpg, is_dst=True), expected)
        self.assertEqual(localize(dt, wpg, is_dst=False), expected)

        dt = datetime(2015, 6, 1, 0)  # CDT
        expected = wpg.localize(dt)

        self.assertEqual(localize(dt, wpg), expected)
        self.assertEqual(localize(dt, wpg, is_dst=None), expected)
        self.assertEqual(localize(dt, wpg, is_dst=GUESS_DST), expected)
        self.assertEqual(localize(dt, wpg, is_dst=True), expected)
        self.assertEqual(localize(dt, wpg, is_dst=False), expected)

    def test_non_existent(self):
        dt = datetime(2015, 3, 8, 2)  # Non-existent time in America/Winnipeg

        with self.assertRaises(NonExistentTimeError):
            localize(dt, wpg)
        with self.assertRaises(NonExistentTimeError):
            localize(dt, wpg, is_dst=None)

        self.assertEqual(
            localize(dt, wpg, is_dst=GUESS_DST),
            wpg.localize(dt),
        )

        with self.assertRaises(NonExistentTimeError):
            localize(dt, wpg, is_dst=True)
        with self.assertRaises(NonExistentTimeError):
            localize(dt, wpg, is_dst=False)

    def test_ambiguous(self):
        dt = datetime(2015, 11, 1, 1)  # Ambiguous time in America/Winnipeg

        with self.assertRaises(AmbiguousTimeError):
            localize(dt, wpg)
        with self.assertRaises(AmbiguousTimeError):
            localize(dt, wpg, is_dst=None)

        self.assertEqual(
            localize(dt, wpg, is_dst=GUESS_DST),
            wpg.localize(dt),
        )
        self.assertEqual(
            localize(dt, wpg, is_dst=True),
            wpg.localize(dt, is_dst=True),
        )
        self.assertEqual(
            localize(dt, wpg, is_dst=False),
            wpg.localize(dt, is_dst=False),
        )


class TestDatetimeExtract(unittest.TestCase):
    def test_basic(self):
        test = '20140102_030405'
        regexp = format_to_regex('%Y%m%d_%H%M%S%f?')

        result = datetime_extract(test, regexp)
        self.assertEqual(result, datetime(2014, 1, 2, 3, 4, 5))

        result = datetime_extract(test + '006', regexp)
        self.assertEqual(result, datetime(2014, 1, 2, 3, 4, 5, 6000))

        result = datetime_extract(test + '06', regexp)
        self.assertEqual(result, datetime(2014, 1, 2, 3, 4, 5, 60000))

        result = datetime_extract(test + '6', regexp)
        self.assertEqual(result, datetime(2014, 1, 2, 3, 4, 5, 600000))

    def test_digits(self):
        test = '20140102_030405'
        regexp = format_to_regex('%Y%m%d_%H%M%S%3f?')

        result = datetime_extract(test, regexp)
        self.assertEqual(result, datetime(2014, 1, 2, 3, 4, 5))

        result = datetime_extract(test + '006', regexp)
        self.assertEqual(result, datetime(2014, 1, 2, 3, 4, 5, 6000))

        # Treated as extra data and ignored.
        result = datetime_extract(test + '06', regexp)
        self.assertEqual(result, datetime(2014, 1, 2, 3, 4, 5))

        # Treated as extra data and ignored.
        result = datetime_extract(test + '6', regexp)
        self.assertEqual(result, datetime(2014, 1, 2, 3, 4, 5))

    def test_anchored(self):
        test = '20140102_030405'
        regexp = format_to_regex('^%Y%m%d_%H%M%S%3f?$')

        result = datetime_extract(test, regexp)
        self.assertEqual(result, datetime(2014, 1, 2, 3, 4, 5))

        result = datetime_extract(test + '006', regexp)
        self.assertEqual(result, datetime(2014, 1, 2, 3, 4, 5, 6000))

        # Anchoring and forcing the width of microseconds causes the
        # expression not to match. Note the exception only occurs when
        # posessive qualifiers.
        self.assertRaises(
            ValueError,
            datetime_extract,
            test + '06',
            regexp,
        )

        self.assertRaises(
            ValueError,
            datetime_extract,
            test + '6',
            regexp,
        )


class TestDatetimeParser(unittest.TestCase):
    def test_empty(self):
        # python-dateutil v2.4.2 was not throwing an exception
        self.assertRaises(ValueError, datetime_parser, '')


class TestRoundDatetime(unittest.TestCase):
    def test_basic(self):
        """
        Basic round_datetime behaviour.
        """
        dt = datetime(2013, 1, 2, 3, 4, 5, 6)
        dt2 = datetime(2013, 1, 2, 3, 4, 31)

        result = round_datetime(dt)
        self.assertEqual(str(result), str(dt))

        result = round_datetime(dt, timedelta(days=1))
        self.assertEqual(str(result), str(datetime(2013, 1, 2)))

        result = round_datetime(dt, timedelta(hours=1))
        self.assertEqual(str(result), str(datetime(2013, 1, 2, 3)))

        result = round_datetime(dt, timedelta(minutes=1))
        self.assertEqual(str(result), str(datetime(2013, 1, 2, 3, 4)))

        result = round_datetime(dt, timedelta(seconds=1))
        self.assertEqual(str(result), str(datetime(2013, 1, 2, 3, 4, 5)))

        result = round_datetime(dt2, timedelta(minutes=1))
        self.assertEqual(str(result), str(datetime(2013, 1, 2, 3, 5)))

    def test_ceil(self):
        """
        Ensure that ceiling doesn't change a rounded datetime.
        """
        dt = datetime(2013, 1, 2, 3, 4, 5, 6)

        result = round_datetime(dt, timedelta(days=1), ceil=True)
        self.assertEqual(str(result), str(datetime(2013, 1, 3)))

        result = round_datetime(dt, timedelta(hours=1), ceil=True)
        self.assertEqual(str(result), str(datetime(2013, 1, 2, 4)))

        result = round_datetime(dt, timedelta(minutes=1), ceil=True)
        self.assertEqual(str(result), str(datetime(2013, 1, 2, 3, 5)))

        # Won't work as units less than seconds are unsupported.
        # result = round_datetime(dt, timedelta(seconds=1), ceil=True)
        # self.assertEqual(str(result), str(datetime(2013, 1, 2, 3, 4, 6)))

    def test_floor(self):
        dt = datetime(2013, 1, 2, 3, 4, 5, 6)

        result = round_datetime(dt, timedelta(days=1), floor=True)
        self.assertEqual(str(result), str(datetime(2013, 1, 2)))

        result = round_datetime(dt, timedelta(hours=1), floor=True)
        self.assertEqual(str(result), str(datetime(2013, 1, 2, 3)))

        result = round_datetime(dt, timedelta(minutes=1), floor=True)
        self.assertEqual(str(result), str(datetime(2013, 1, 2, 3, 4)))

        result = round_datetime(dt, timedelta(seconds=1), floor=True)
        self.assertEqual(str(result), str(datetime(2013, 1, 2, 3, 4, 5)))

    def test_rounded(self):
        """
        Ensure that a rounded datetimes are unchanged when it is
        rounded again.
        """
        dt = datetime(2013, 1, 2, 3)
        interval = timedelta(hours=1)

        result = round_datetime(dt, interval)
        self.assertEqual(str(result), str(dt))

        result = round_datetime(dt, interval, ceil=True)
        self.assertEqual(str(result), str(dt))

        result = round_datetime(dt, interval, floor=True)
        self.assertEqual(str(result), str(dt))

    def test_timezone(self):
        """
        Basic timezone support for round_datetime.
        """
        test = {
            'dt': datetime(2013, 1, 2, 3, 4, 5, tzinfo=utc),
            'interval': timedelta(hours=1),
        }
        expected = datetime(2013, 1, 2, 3, tzinfo=utc)

        result = round_datetime(**test)

        self.assertEqual(str(result), str(expected))

    def test_daylight_saving_transistion(self):
        """
        Rounding over a daylight saving time transition.
        """
        amsterdam = timezone('Europe/Amsterdam')
        test = {
            'dt': amsterdam.localize(datetime(2002, 10, 27, 12)),
            'interval': timedelta(days=1),
            'floor': True,
        }
        expected = amsterdam.localize(datetime(2002, 10, 27))

        result = round_datetime(**test)

        self.assertEqual(str(result), str(expected))

    def test_tzinfo_dst_issue(self):
        """
        Rounding on badly contructed timezone aware datetimes.

        Sometimes timezone aware datetimes can be badly constructed. We
        should fix these issues so that rounding completes successfully.

        Read this for details on badly created datetimes.
        http://pytz.sourceforge.net/#localized-times-and-date-arithmetic
        """
        amsterdam = timezone('Europe/Amsterdam')
        test = {
            # Don't set timezones like this!
            'dt': datetime(2002, 10, 28, 12, tzinfo=amsterdam),
            'interval': timedelta(days=1),
            'floor': True,
        }
        expected = amsterdam.localize(datetime(2002, 10, 28))

        result = round_datetime(**test)

        self.assertEqual(result, expected)

    def test_relativedelta(self):
        """
        Rounding to a relativedelta.
        """
        eastern = timezone('US/Eastern')
        test = {
            'dt': eastern.localize(datetime(2013, 6, 15)),
            'interval': relativedelta(years=1),
            'floor': True,
        }
        expected = eastern.localize(datetime(2013, 1, 1))

        result = round_datetime(**test)

        self.assertEqual(result, expected)

    def test_relativedelta_ceil_issue(self):
        """
        Ensure ceiling with relativedelta doesn't change a rounded datetime.
        """
        eastern = timezone('US/Eastern')
        test = {
            'dt': eastern.localize(datetime(2013, 1, 1)),
            'interval': relativedelta(years=1),
            'ceil': True,
        }
        expected = eastern.localize(datetime(2013, 1, 1))

        result = round_datetime(**test)

        self.assertEqual(result, expected)

    def test_relativedelta_before_epoch(self):
        """
        Relativedelta rounding prior to epoch

        Due to how we are performing rounding for relativedelta's
        dates before the UNIX epoch are handled slightly differently.
        """
        eastern = timezone('US/Eastern')
        test = {
            'dt': eastern.localize(datetime(1960, 6, 15)),
            'interval': relativedelta(years=1),
            'floor': True,
        }
        expected = eastern.localize(datetime(1960, 1, 1))

        result = round_datetime(**test)

        self.assertEqual(result, expected)

    def test_relativedelta_timezone_issue(self):
        """
        Relativedelta rounding over a daylight saving time transition.
        """
        eastern = timezone('US/Eastern')
        test = {
            'dt': eastern.localize(datetime(2014, 4, 1)),
            'interval': relativedelta(months=1),
            'floor': True,
        }
        expected = eastern.localize(datetime(2014, 4, 1))

        result = round_datetime(**test)

        self.assertEqual(result, expected)

    def test_relativedelta_increment_zero(self):
        """
        Relativedelta rounding using zero.
        """
        # Note: Mispelled keywords in relativedelta calls are effectively
        # zero. ie. relativedelta(month=0) == relativedelta(0)

        test = {
            'dt': datetime(2000, 6, 1),
            'interval': relativedelta(0),
            'floor': True,
        }
        expected = datetime(2000, 6, 1)

        result = round_datetime(**test)

        self.assertEqual(result, expected)


class TestRoundTimedelta(unittest.TestCase):
    def test_basic(self):
        # Ties
        delta = round_timedelta(timedelta(minutes=30), timedelta(hours=1))
        self.assertEqual(delta, timedelta(hours=1))

        # Ties below
        delta = round_timedelta(timedelta(minutes=1), timedelta(hours=1))
        self.assertEqual(delta, timedelta(hours=0))

        # Ties above
        delta = round_timedelta(timedelta(minutes=59), timedelta(hours=1))
        self.assertEqual(delta, timedelta(hours=1))

        # Corner cases
        delta = round_timedelta(timedelta(minutes=0), timedelta(hours=1))
        self.assertEqual(delta, timedelta(hours=0))
        delta = round_timedelta(timedelta(minutes=60), timedelta(hours=1))
        self.assertEqual(delta, timedelta(hours=1))


class TestLocalizePeriod(unittest.TestCase):
    def test_localize_period_ending(self):
        dt0 = datetime(2015, 3, 8, 2)  # Non-existent time in America/Winnipeg
        dt1 = datetime(2015, 3, 8, 3)

        with self.assertRaises(NonExistentTimeError):
            localize_period_ending(dt1, wpg, timedelta(hours=1))

        for i in range(2, 10):
            self.assertIsNotNone(
                localize_period_ending(dt0, wpg, timedelta(hours=i))
            )
            self.assertIsNotNone(
                localize_period_ending(dt1, wpg, timedelta(hours=i))
            )

    def test_localize_hour_ending(self):
        dt0 = datetime(2015, 3, 8, 2)  # Non-existent time in America/Winnipeg
        dt1 = datetime(2015, 3, 8, 3)

        self.assertIsNotNone(localize_hour_ending(dt0, wpg))

        with self.assertRaises(NonExistentTimeError):
            localize_hour_ending(dt1, wpg)


class TestTimezoneTransitionList(unittest.TestCase):
    def test_list_timezone_transitions(self):
        with self.assertRaises(TypeError):
            timezone_transitions(utc)

        allWpgTransitions = list(timezone_transitions(wpg))
        oneYearWpgTransition = list(timezone_transitions(wpg, 1996))

        self.assertEqual(len(oneYearWpgTransition), 2)
        self.assertGreater(len(allWpgTransitions), 2)


class TestEstimate(unittest.TestCase):
    def test_pjm_da_shadow_prices(self):
        # Release Date      Content End
        # 2015-02-18 09:59  2014-01-01
        # 2015-02-18 09:59  2015-01-01
        # 2016-01-04 16:54  2016-01-01
        # 2016-01-18 16:18  2016-01-20
        # 2016-01-19 16:18  2016-01-21
        # 2016-01-20 16:18  2016-01-22
        eastern = timezone("US/Eastern")
        dates = [
            localize(datetime(2014, 6, 1), eastern),
            localize(datetime(2015, 8, 1), eastern),
            localize(datetime(2016, 1, 2), eastern),
            localize(datetime(2016, 1, 15), eastern),
            localize(datetime(2016, 1, 18, 13), eastern),
        ]
        expected = [
            (
                localize(datetime(2014, 5, 31, 13), eastern),
                localize(datetime(2014, 6, 2, 0), eastern),
            ),
            (
                localize(datetime(2015, 7, 31, 13), eastern),
                localize(datetime(2015, 8, 2, 0), eastern),
            ),
            (
                localize(datetime(2016, 1, 1, 13), eastern),
                localize(datetime(2016, 1, 3, 0), eastern),
            ),
            (
                localize(datetime(2016, 1, 14, 13), eastern),
                localize(datetime(2016, 1, 16, 0), eastern),
            ),
            (
                localize(datetime(2016, 1, 18, 13), eastern),
                localize(datetime(2016, 1, 20, 0), eastern),
            ),
        ]
        publish_interval = timedelta(days=1)
        publish_offset = timedelta(hours=13)
        content_interval = timedelta(days=1)
        content_offset = timedelta(days=2)

        for i in range(len(dates)):
            release_date = estimate_latest_release(
                dates[i], publish_interval, publish_offset,
            )
            self.assertEqual(release_date, expected[i][0])

            content_end = estimate_content_end(
                release_date, content_interval, content_offset,
            )
            self.assertEqual(content_end, expected[i][1])

            release_date2, content_end2 = estimate_latest(dates[i], (
                publish_interval, publish_offset, content_interval, content_offset
            ))

            self.assertEqual(release_date, release_date2)
            self.assertEqual(content_end, content_end2)

class TestDateTimeSplit(unittest.TestCase):
    def test_datetime_split(self):
        from inveniautils.datetime_range import DatetimeRange, Bound

        pivot = datetime(2020, 1, 2, tzinfo=utc)

        d0 = datetime(2019, 1, 1, tzinfo=utc)
        d1 = datetime(2020, 1, 1, tzinfo=utc)
        d2 = datetime(2021, 1, 1, tzinfo=utc)

        d3 = datetime(2019, 12, 31, tzinfo=utc)
        d4 = datetime(2020, 1, 3, tzinfo=utc)

        r0 = DatetimeRange(d0, d2)
        r1 = DatetimeRange(d0, d1)
        r2 = DatetimeRange(d1, d2)

        expected = (
            [DatetimeRange(d0, pivot, bounds=(Bound.INCLUSIVE, Bound.EXCLUSIVE)),
             DatetimeRange(d0, d1),
             DatetimeRange(d1, pivot, bounds=(Bound.INCLUSIVE, Bound.EXCLUSIVE)),
             d3],
            [DatetimeRange(pivot, d2), DatetimeRange(pivot, d2), d4],
        )

        actual = split([r0, r1, r2, d3, d4], pivot)

        self.assertEqual(actual, expected)

class TestDateTimeContains(unittest.TestCase):
    def test_contains(self):
        from inveniautils.datetime_range import DatetimeRange

        d0 = datetime(2019, 1, 1, tzinfo=utc)
        d1 = datetime(2020, 1, 1, tzinfo=utc)
        d2 = datetime(2021, 1, 1, tzinfo=utc)
        d3 = datetime(2020, 1, 3, tzinfo=utc)

        self.assertTrue(contains(DatetimeRange(d1, d2), d3))
        self.assertTrue(contains(DatetimeRange(d0, d2), d3))
        self.assertFalse(contains(DatetimeRange(d0, d1), d3))
        self.assertFalse(contains(DatetimeRange(d1, d1), d3))
        self.assertTrue(contains(DatetimeRange(d1, d1), d1))
        self.assertTrue(contains(d1, d1))
        self.assertFalse(contains(d1, d2))
        self.assertFalse(contains(None, d1))


class TestTimezoneParser(unittest.TestCase):
    def test_timezone_parse(self):
        self.assertEqual(timezone_util('utc', None), utc)
        self.assertEqual(timezone_util(None, 0), utc)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
