import unittest
from inveniautils.timer import Timer, EstimatedTimeToCompletion
from random import randint
from datetime import timedelta


class TestTimer(unittest.TestCase):
    def test_timer_automatically_starts_in_with(self):
        with Timer(timer=MockTimer()) as t:
            self.assertTrue(t.running)
            self.assertRaises(ValueError, lambda: t.start())
            t.stop()
            self.assertRaises(ValueError, lambda: t.stop())
            t.start()

    def test_timer_elapsed(self):
        mock = MockTimer()
        t = Timer(timer=mock)

        self.assertFalse(t.running)
        t.start()
        self.assertTrue(t.running)

        self.assertEqual(t.elapsed, timedelta(0))

        for i in range(100):
            rand = randint(1, 1000)
            mock.set_time(rand)
            self.assertEqual(t.elapsed, timedelta(seconds=rand))

    def test_timer_autostart(self):
        mock = MockTimer()
        t = Timer(start=True, timer=mock)

        self.assertTrue(t.running)

    def test_timer_tic_toc(self):
        mock = MockTimer()
        t = Timer(timer=mock)

        self.assertFalse(t.running)
        t.tic()
        self.assertTrue(t.running)
        t.toc()
        self.assertFalse(t.running)

    def test_estimation_test(self):
        mock = MockTimer()

        # The test breaks if time starts at 0, thankfully that will never
        # happen in reality.
        mock.set_time(1)

        val = EstimatedTimeToCompletion.test(121, 1, mock)

        self.assertEqual(val, timedelta(minutes=2))

    def test_estimation_accuracy(self):
        mock = MockTimer()
        mock.set_time(10)

        estimator = EstimatedTimeToCompletion(10, timer=mock)
        list = []
        expected = [
            None,
            timedelta(seconds=0),
            timedelta(seconds=4),
            timedelta(seconds=7),
            timedelta(seconds=9),
            timedelta(seconds=10),
            timedelta(seconds=10),
            timedelta(seconds=9),
            timedelta(seconds=7),
            timedelta(seconds=4),
        ]
        for i in range(10):
            list.append(estimator.report())
            mock.sleep(i)

        for actual, expect in zip(list, expected):
            self.assertEqual(actual, expect)

        estimator.reset()
        self.assertEqual(estimator.elapsed, timedelta(0))


class MockTimer(object):
    def __init__(self):
        self._time = 0

    def set_time(self, time):
        self._time = time

    def sleep(self, time):
        self._time += time

    def time(self):
        return self._time
