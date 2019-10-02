import copy
import logging
import unittest
import math
from datetime import datetime, timedelta

from inveniautils.limiter import Limiter, Status, StatusHistory, StaticLimiter

from pytz import utc

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class IntervalEmulator(object):
    def __init__(self, limiter, now=None):
        if now is None:
            now = datetime.fromtimestamp(0, utc)

        self.limiter = limiter
        self.now = now

    def emulate(self, optimal_interval=None):
        # Pretend like time has passed due to throttling.
        self.now += timedelta(seconds=self.limiter.interval)

        # Pretend like performed some operation that returned a status.
        if optimal_interval is not None:
            success = self.limiter.interval >= optimal_interval
        else:
            success = None

        # Report the status to the limiter.
        self.limiter.status(success, self.now)

        return success

    def emulate_til_successful(self, optimal_interval, max_attempts=50):
        attempts = 0
        success = False

        logger.debug("OPTIMAL {}".format(optimal_interval))
        while attempts == 0 or not success:
            attempts += 1

            success = self.emulate(optimal_interval)

            if attempts > max_attempts:
                raise RuntimeError("Emulation appears to have infinite loop")

        return attempts


class DateEmulator(object):
    def __init__(self, limiter, now=None):
        if now is None:
            now = datetime.fromtimestamp(0, utc)

        self.limiter = limiter
        self.now = now

    def emulate(self, target_date=None):
        # Pretend like time has passed due to throttling.
        self.now += timedelta(seconds=self.limiter.delay(self.now))

        # Pretend like performed some operation that returned a status.
        if target_date is not None:
            success = self.now >= target_date
        else:
            success = None

        # Report the status to the limiter.
        self.limiter.status(success, self.now)

        return success

    def emulate_til_successful(self, target_date, max_attempts=50):
        attempts = 0
        success = False

        if logger.isEnabledFor(logging.DEBUG):
            print('')  # Print empty line
        logger.debug("TARGET_DATE {}".format(target_date))

        while not success:
            attempts += 1

            success = self.emulate(target_date)

            if attempts > max_attempts:
                raise RuntimeError("Emulation appears to have infinite loop")

        return attempts


class TestLimiter(unittest.TestCase):
    def test_basic(self):
        # Starting at 1 gives us nice powers of 2.
        limiter = Limiter(1)
        env = IntervalEmulator(limiter)

        self.assertEqual(limiter.interval, 1)

        # Find the first successful interval.
        attempts = env.emulate_til_successful(121)
        self.assertEqual(attempts, 9)
        self.assertEqual(limiter.success_interval, 128)

        # Optimize the interval.
        attempts = env.emulate_til_successful(121)
        self.assertEqual(attempts, 4)
        self.assertEqual(limiter.success_interval, 124)

        # Optimize the interval again.
        attempts = env.emulate_til_successful(121)
        self.assertEqual(attempts, 1)
        self.assertEqual(limiter.success_interval, 122)

        # Found the optimal interval.
        attempts = env.emulate_til_successful(121)
        self.assertEqual(attempts, 1)
        self.assertEqual(limiter.success_interval, 121)

        # Perform one more emulation round to ensure there are no
        # infinite loops.
        attempts = env.emulate_til_successful(121)
        self.assertEqual(attempts, 2)
        self.assertEqual(limiter.success_interval, 121)

    def test_realistic(self):
        # Starting at 1 gives us nice powers of 2.
        limiter = Limiter(1)
        env = IntervalEmulator(limiter)

        self.assertEqual(limiter.interval, 1)

        # First request should always work since it has been "Inf" since
        # last request.
        attempts = env.emulate_til_successful(0)
        self.assertEqual(attempts, 1)
        self.assertEqual(limiter.success_interval, None)

        attempts = env.emulate_til_successful(121)
        self.assertEqual(attempts, 8)
        self.assertEqual(limiter.success_interval, 128)

        attempts = env.emulate_til_successful(121)
        self.assertEqual(attempts, 4)
        self.assertEqual(limiter.success_interval, 124)

        attempts = env.emulate_til_successful(121)
        self.assertEqual(attempts, 1)
        self.assertEqual(limiter.success_interval, 122)

        attempts = env.emulate_til_successful(121)
        self.assertEqual(attempts, 1)
        self.assertEqual(limiter.success_interval, 121)

    def test_fluctuating_honing(self):
        # Starting at 1 gives us nice powers of 2.
        limiter = Limiter(1)
        env = IntervalEmulator(limiter)

        self.assertEqual(limiter.interval, 1)

        env.emulate(7)
        self.assertEqual(limiter.interval, 1)

        env.emulate(7)
        self.assertEqual(limiter.interval, 2)

        env.emulate(7)
        self.assertEqual(limiter.interval, 4)

        env.emulate(7)
        self.assertEqual(limiter.interval, 8)

        env.emulate(7)
        self.assertEqual(limiter.interval, 6)

        # Modify valid delay when honing in.
        env.emulate(9)
        self.assertEqual(limiter.interval, 7)

        env.emulate(9)
        self.assertEqual(limiter.interval, 8)

        env.emulate(9)
        self.assertEqual(limiter.interval, 10)

        env.emulate(9)
        self.assertEqual(limiter.interval, 9)

        env.emulate(9)
        self.assertEqual(limiter.interval, 8)

    def test_fluctuating(self):
        # Starting at 1 gives us nice powers of 2.
        limiter = Limiter(1)
        env = IntervalEmulator(limiter)

        self.assertEqual(limiter.interval, 1)

        env.emulate_til_successful(121)
        # self.assertEqual(limiter.last_failure_interval, 64)
        self.assertEqual(limiter.success_interval, 128)

        # Set goal to be just outside of the last successful interval.
        env.emulate_til_successful(129)
        # self.assertEqual(limiter.last_failure_interval, 128)
        self.assertEqual(limiter.success_interval, 130)

        # Set goal to be earlier. Should work on the first attempt.
        attempts = env.emulate_til_successful(33)
        self.assertEqual(attempts, 1)
        # self.assertEqual(limiter.last_failure_interval, None)
        self.assertEqual(limiter.success_interval, 129)

    def test_hostile_reporting(self):
        # Starting at 1 gives us nice powers of 2.
        limiter = Limiter(1)
        now = datetime.fromtimestamp(0, utc)

        self.assertEqual(limiter.interval, 1)

        # Perform initialize report.
        limiter.status(False, now)
        self.assertEqual(limiter.interval, 1)

        # Pretend like a second has passed and report.
        now += timedelta(seconds=1)
        limiter.status(False, now)
        self.assertEqual(limiter.interval, 2)

        # Report for the same time again but with a different status.
        limiter.status(True, now)
        self.assertIn(limiter.interval, [1, 2])

    def test_decreasing(self):
        # Starting at 1 gives us nice powers of 2.
        limiter = Limiter(8)
        env = IntervalEmulator(limiter)

        self.assertEqual(limiter.interval, 8)

        env.emulate(3)
        self.assertEqual(limiter.interval, 8)

        env.emulate(3)
        self.assertEqual(limiter.interval, 7)

        env.emulate(3)
        self.assertEqual(limiter.interval, 5)

        env.emulate(3)
        self.assertEqual(limiter.interval, 1)

        env.emulate(3)
        self.assertEqual(limiter.interval, 3)

    def test_ignorant(self):
        limiter = Limiter(8)
        now = datetime.fromtimestamp(0, utc)

        # Starting delay should be 8.
        self.assertEqual(limiter.interval, 8)
        self.assertEqual(limiter.adjustment, 0)

        # Initial request will be successful due so starting delay will
        # not change.
        limiter.status(True, now)
        self.assertEqual(limiter.interval, 8)
        self.assertEqual(limiter.adjustment, 0)

        # Ignore Limiter throttling and request 2 seconds later.
        now += timedelta(seconds=2)
        limiter.status(2 >= 3, now)
        self.assertEqual(limiter.interval, 8)  # Unchanged still.
        self.assertEqual(limiter.adjustment, 0)

        # Ignore Limiter delay and request 4 seconds later.
        # Since we'll have found a valid and invalid datapoints we can
        # try to hone in on a optimal delay.
        now += timedelta(seconds=4)
        limiter.status(4 >= 3, now)
        self.assertEqual(limiter.interval, 3)  # Honed in delay
        self.assertEqual(limiter.adjustment, 0)

    def test_reported_time_decreasing(self):
        # Starting at 1 gives us nice powers of 2.
        limiter = Limiter(1)
        now = datetime.fromtimestamp(0, utc)

        limiter.status(False, now)

        now -= timedelta(seconds=1)
        with self.assertRaises(ValueError):
            limiter.status(True, now)

    def test_throttle(self):
        limiter = Limiter(initial_interval=1)

        # Attempt to throttle before we have enough information. Should
        # sleep for 0 seconds.
        start = datetime.now()
        limiter.throttle()
        duration = datetime.now() - start
        self.assertLess(duration, timedelta(seconds=1))

        # Perform the initial report.
        limiter.status(False)

        # Throttle for 1 second (defined by initial_interval).
        start = datetime.now()
        limiter.throttle()
        duration = datetime.now() - start
        self.assertGreater(duration, timedelta(seconds=1))

    def test_max_adjustment(self):
        limiter = Limiter()
        limiter.adjustment = -1
        history = StatusHistory()
        history.add(Status(datetime.now(utc) - timedelta(seconds=10), False))
        try:
            for i in range(0, 50):
                limiter.interval = 0
                limiter.history = copy.deepcopy(history)
                limiter.status(success=False)
            self.assertLess(limiter.adjustment, timedelta.max.total_seconds())
        except OverflowError:
            self.fail('Adjustment Values too large')

    def test_min_adjustment(self):
        limiter = Limiter()
        limiter.adjustment = -1
        history = StatusHistory()
        history.add(Status(datetime.now(utc) - timedelta(seconds=10), False))
        try:
            for i in range(0, 50):
                limiter.interval = 0
                limiter.history = copy.deepcopy(history)
                limiter.status(success=True)
            self.assertGreater(limiter.adjustment, timedelta.min.total_seconds())  # noqa: E501
        except OverflowError:
            self.fail('Adjustment Values too negatively large')


class TestStaticLimiter(unittest.TestCase):
    def test_throttle(self):
        limiter = StaticLimiter(interval=0.1)
        self.assertEqual(limiter.throttle(), 0)
        self.assertTrue(math.isclose(limiter.throttle(), 0.1, rel_tol=0.01))
        limiter.status()
        self.assertTrue(math.isclose(limiter.throttle(), 0.1, rel_tol=0.01))


class TestScheduling(unittest.TestCase):
    def test_discovery(self):
        # Ensure that we can discover the publication interval of a
        # source.
        #
        # Properties of this test:
        # - First target date will always pass on the first status check.
        # - Requires the use of the binary search or else it will skip a
        #   target.

        limiter = Limiter(
            min_interval=600,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 1, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 6,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 4, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 5, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 6, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 7, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 8, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 9, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 10, 20, tzinfo=utc): 2,
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            attempts = env.emulate_til_successful(target_date)

            self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # Ensure that stable is working correctly.
            if limiter.stable:
                self.assertEqual(attempts, 2)
                self.assertEqual(env.now, target_date)

    def test_discovery_minutes(self):
        # Ensure that we can discover the publication interval of a
        # source.
        #
        # Properties of this test:
        # - Shows how the binary search can be inefficient if used
        #   too aggressively.

        limiter = Limiter(
            min_interval=60,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 1, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 6,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 9,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 4, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 5, 20, tzinfo=utc): 5,
            datetime(2000, 1, 1, 6, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 7, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 8, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 9, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 10, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 11, 20, tzinfo=utc): 3,
            datetime(2000, 1, 1, 12, 20, tzinfo=utc): 4,
            datetime(2000, 1, 1, 13, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 14, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 15, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 16, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 17, 20, tzinfo=utc): 2,
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            attempts = env.emulate_til_successful(target_date)

            self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # Ensure that stable is working correctly.
            if limiter.stable:
                self.assertEqual(attempts, 2)
                self.assertEqual(env.now, target_date)

    def test_discovery_seconds(self):
        # Ensure that we can discover the publication interval of a
        # source.
        #
        # Properties of this test:
        # - Shows how the binary search can be inefficient if used
        #   too aggressively.

        limiter = Limiter(
            min_interval=1,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 1, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 12,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 20,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 17,
            datetime(2000, 1, 1, 4, 20, tzinfo=utc): 15,
            datetime(2000, 1, 1, 5, 20, tzinfo=utc): 9,
            datetime(2000, 1, 1, 6, 20, tzinfo=utc): 6,
            datetime(2000, 1, 1, 7, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 8, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 9, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 10, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 11, 20, tzinfo=utc): 6,
            datetime(2000, 1, 1, 12, 20, tzinfo=utc): 3,
            datetime(2000, 1, 1, 13, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 14, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 15, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 16, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 17, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 18, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 19, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 20, 20, tzinfo=utc): 2,
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            attempts = env.emulate_til_successful(target_date)

            self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # Ensure that stable is working correctly.
            if limiter.stable:
                self.assertEqual(attempts, 2)
                self.assertEqual(env.now, target_date)

    def test_discovery_7_minutes(self):
        # Ensure that publication intervals which are not divisible by
        # the min_interval can still behave reasonibly.

        limiter = Limiter(
            min_interval=60 * 7,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 1, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 3,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 4,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 4, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 5, 20, tzinfo=utc): 4,
            datetime(2000, 1, 1, 6, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 7, 20, tzinfo=utc): 3,
            datetime(2000, 1, 1, 8, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 9, 20, tzinfo=utc): 3,
            datetime(2000, 1, 1, 10, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 11, 20, tzinfo=utc): 3,
            datetime(2000, 1, 1, 12, 20, tzinfo=utc): 2,  # 12:26
            datetime(2000, 1, 1, 13, 20, tzinfo=utc): 1,  # 13:22
            datetime(2000, 1, 1, 14, 20, tzinfo=utc): 3,  # 14:25
            datetime(2000, 1, 1, 15, 20, tzinfo=utc): 1,  # 15:21
            datetime(2000, 1, 1, 16, 20, tzinfo=utc): 3,  # 16:24
            datetime(2000, 1, 1, 17, 20, tzinfo=utc): 1,  # 17:20
            datetime(2000, 1, 1, 18, 20, tzinfo=utc): 3,  # 18:23
            datetime(2000, 1, 1, 19, 20, tzinfo=utc): 2,  # 19:26
            datetime(2000, 1, 1, 20, 20, tzinfo=utc): 1,  # 20:22
            datetime(2000, 1, 1, 21, 20, tzinfo=utc): 3,  # 21:25
            datetime(2000, 1, 1, 22, 20, tzinfo=utc): 1,  # 22:21
            datetime(2000, 1, 1, 23, 20, tzinfo=utc): 3,  # 23:24
            datetime(2000, 1, 2, 0, 20, tzinfo=utc): 1,   # 00:20
            datetime(2000, 1, 2, 1, 20, tzinfo=utc): 3,   # 01:23
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            attempts = env.emulate_til_successful(target_date)

            self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # Ensure that stable is working correctly.
            # if limiter.stable:
            #     self.assertEqual(attempts, 2)
            #     self.assertEqual(env.now, target_date)

    def test_shift_earlier(self):
        limiter = Limiter(
            initial_interval=3600,
            min_interval=600,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 0, 20, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 2,
            # Shift occurs.
            datetime(2000, 1, 1, 3, 50, tzinfo=utc): 1,
            datetime(2000, 1, 1, 4, 50, tzinfo=utc): 1,
            datetime(2000, 1, 1, 5, 50, tzinfo=utc): 4,
            datetime(2000, 1, 1, 6, 50, tzinfo=utc): 1,
            datetime(2000, 1, 1, 7, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 8, 50, tzinfo=utc): 2,
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            attempts = env.emulate_til_successful(target_date)

            self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # TODO: Need to update stable to switch to false if we
            # aren't in the TFT pattern.
            # Ensure that stable is working correctly.
            # if limiter.stable:
            #     self.assertEqual(attempts, 2)
            #     self.assertEqual(env.now, target_date)

    def test_shift_later(self):
        limiter = Limiter(
            initial_interval=3600,
            min_interval=600,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 0, 20, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 2,
            # Shift occurs.
            datetime(2000, 1, 1, 4, 50, tzinfo=utc): 5,
            datetime(2000, 1, 1, 5, 50, tzinfo=utc): 1,
            datetime(2000, 1, 1, 6, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 7, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 8, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 9, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 10, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 11, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 12, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 13, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 14, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 15, 50, tzinfo=utc): 2,
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            attempts = env.emulate_til_successful(target_date)

            self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # TODO: Need to update stable to switch to false if we
            # aren't in the TFT pattern.
            # Ensure that stable is working correctly.
            # if limiter.stable:
            #     self.assertEqual(attempts, 2)
            #     self.assertEqual(env.now, target_date)

    def test_late(self):
        limiter = Limiter(
            initial_interval=3600,
            min_interval=600,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 0, 20, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 4, 25, tzinfo=utc): 3,  # Late
            datetime(2000, 1, 1, 5, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 6, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 7, 20, tzinfo=utc): 3,
            datetime(2000, 1, 1, 8, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 9, 20, tzinfo=utc): 2,
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            attempts = env.emulate_til_successful(target_date)

            self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # TODO: Need to update stable to switch to false if we
            # aren't in the TFT pattern.
            # Ensure that stable is working correctly.
            # if limiter.stable:
            #     self.assertEqual(attempts, 2)
            #     self.assertEqual(env.now, target_date)

    # Stability override fault
    @unittest.expectedFailure
    def test_freq_change(self):
        limiter = Limiter(
            initial_interval=3600,
            min_interval=600,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 0, 20, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 2,
            # Frequency change.
            datetime(2000, 1, 1, 3, 50, tzinfo=utc): 1,
            datetime(2000, 1, 1, 4, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 4, 50, tzinfo=utc): 1,
            datetime(2000, 1, 1, 5, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 5, 50, tzinfo=utc): 3,
            datetime(2000, 1, 1, 6, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 6, 50, tzinfo=utc): 1,
            datetime(2000, 1, 1, 7, 20, tzinfo=utc): 3,
            datetime(2000, 1, 1, 7, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 8, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 8, 50, tzinfo=utc): 2,
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            # attempts = env.emulate_til_successful(target_date)

            # self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # TODO: Need to update stable to switch to false if we
            # aren't in the TFT pattern.
            # Ensure that stable is working correctly.
            # if limiter.stable:
            #     self.assertEqual(attempts, 2)
            #     self.assertEqual(env.now, target_date)

    def test_skip(self):
        limiter = Limiter(
            initial_interval=3600,
            min_interval=600,
            # max_interval=3600,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 0, 20, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 2,
            # Skipped
            datetime(2000, 1, 1, 5, 20, tzinfo=utc): 8,
            datetime(2000, 1, 1, 6, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 7, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 8, 20, tzinfo=utc): 2,
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            attempts = env.emulate_til_successful(target_date)

            self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # TODO: Need to update stable to switch to false if we
            # aren't in the TFT pattern.
            # Ensure that stable is working correctly.
            # if limiter.stable:
            #     self.assertEqual(attempts, 2)
            #     self.assertEqual(env.now, target_date)

    @unittest.expectedFailure
    def test_skip_and_freq_change(self):
        limiter = Limiter(
            initial_interval=3600,
            min_interval=600,
            max_interval=3600,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 0, 20, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 2,
            # Skipped
            datetime(2000, 1, 1, 5, 20, tzinfo=utc): 6,
            datetime(2000, 1, 1, 5, 50, tzinfo=utc): 1,
            datetime(2000, 1, 1, 6, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 6, 50, tzinfo=utc): 1,
            datetime(2000, 1, 1, 7, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 7, 50, tzinfo=utc): 2,
            datetime(2000, 1, 1, 8, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 8, 50, tzinfo=utc): 2,
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            # attempts = env.emulate_til_successful(target_date)

            # self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # TODO: Need to update stable to switch to false if we
            # aren't in the TFT pattern.
            # Ensure that stable is working correctly.
            # if limiter.stable:
            #     self.assertEqual(attempts, 2)
            #     self.assertEqual(env.now, target_date)

    @unittest.expectedFailure
    def test_tuning_nightmare_seconds(self):
        limiter = Limiter(
            min_interval=1,
            since_success=True,
        )
        now = datetime(2000, 1, 1, 1, tzinfo=utc)
        env = DateEmulator(limiter, now)

        interval = timedelta(hours=1)
        target_date_attempts = {
            datetime(2000, 1, 1, 0, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 1, 20, tzinfo=utc): 12,
            datetime(2000, 1, 1, 2, 20, tzinfo=utc): 20,
            datetime(2000, 1, 1, 3, 20, tzinfo=utc): 17,
            datetime(2000, 1, 1, 4, 20, tzinfo=utc): 15,
            datetime(2000, 1, 1, 5, 20, tzinfo=utc): 9,
            datetime(2000, 1, 1, 6, 20, tzinfo=utc): 6,
            datetime(2000, 1, 1, 7, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 8, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 9, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 10, 20, tzinfo=utc): 1,  # Tuning
            # datetime(2000, 1, 1, 11, 20, tzinfo=utc): 5,
            datetime(2000, 1, 1, 12, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 13, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 14, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 15, 20, tzinfo=utc): 4,
            datetime(2000, 1, 1, 16, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 17, 20, tzinfo=utc): 1,
            datetime(2000, 1, 1, 18, 20, tzinfo=utc): 3,
            datetime(2000, 1, 1, 19, 20, tzinfo=utc): 2,
            datetime(2000, 1, 1, 20, 20, tzinfo=utc): 2,
        }

        for target_date, expected_attempts in sorted(target_date_attempts.items()):  # noqa: E501
            attempts = env.emulate_til_successful(target_date)

            # self.assertEqual(attempts, expected_attempts)

            # Ensure that we never delay so long that we miss a target.
            self.assertGreaterEqual(env.now, target_date)
            self.assertTrue(env.now - target_date < interval)

            # Ensure that stable is working correctly.
            if limiter.stable:
                self.assertEqual(attempts, 2)
                self.assertEqual(env.now, target_date)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
