import unittest
from math import isclose
from inveniautils.weather import dewpoint_si


class TestWeather(unittest.TestCase):
    def test_dewpoint_valid(self):
        actual = [
            dewpoint_si(316.2, rel_humidity=0.1),
            dewpoint_si(316.2, wet_bulb=281.5, elevation=10),
            dewpoint_si(316.2, wet_bulb=281.5, pressure=101181),
        ]
        expected = [
            278.0495621235539,
            278.02384811394785,
            278.02388062160657,
        ]

        for act, exp in zip(actual, expected):
            self.assertTrue(isclose(act, exp, rel_tol=1e-7))

    def test_dewpoint_invalid(self):
        self.assertRaises(RuntimeError, lambda: dewpoint_si(316.2))
