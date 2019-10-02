import logging
import unittest
import math

from inveniautils import mathutil
from inveniautils.mathutil import RoundingMode, round_to


class TestRoundTo(unittest.TestCase):
    def test_basic(self):
        # Default rounding mode is NEAREST_TIES_FROM_ZERO

        # Ties
        self.assertEqual(round_to(5.5, 1), 6.0)
        self.assertEqual(round_to(5.5, -1), 6.0)
        self.assertEqual(round_to(-5.5, 1), -6.0)
        self.assertEqual(round_to(-5.5, -1), -6.0)

        # Below tie
        self.assertEqual(round_to(5.1, 1), 5.0)
        self.assertEqual(round_to(5.1, -1), 5.0)
        self.assertEqual(round_to(-5.1, 1), -5.0)
        self.assertEqual(round_to(-5.1, -1), -5.0)

        # Above tie
        self.assertEqual(round_to(5.8, 1), 6.0)
        self.assertEqual(round_to(5.8, -1), 6.0)
        self.assertEqual(round_to(-5.8, 1), -6.0)
        self.assertEqual(round_to(-5.8, -1), -6.0)

    def test_basic_round_up(self):
        mode = RoundingMode.UP

        # Ties
        self.assertEqual(round_to(5.5, 1, mode), 6.0)
        self.assertEqual(round_to(5.5, -1, mode), 6.0)
        self.assertEqual(round_to(-5.5, 1, mode), -5.0)
        self.assertEqual(round_to(-5.5, -1, mode), -5.0)

        # Below tie
        self.assertEqual(round_to(5.1, 1, mode), 6.0)
        self.assertEqual(round_to(5.1, -1, mode), 6.0)
        self.assertEqual(round_to(-5.1, 1, mode), -5.0)
        self.assertEqual(round_to(-5.1, -1, mode), -5.0)

        # Above tie
        self.assertEqual(round_to(5.8, 1, mode), 6.0)
        self.assertEqual(round_to(5.8, -1, mode), 6.0)
        self.assertEqual(round_to(-5.8, 1, mode), -5.0)
        self.assertEqual(round_to(-5.8, -1, mode), -5.0)

        # Corner cases
        self.assertEqual(round_to(0, 1, mode), 0)
        self.assertEqual(round_to(0, -1, mode), 0)
        self.assertEqual(round_to(1, 1, mode), 1)
        self.assertEqual(round_to(1, -1, mode), 1)
        self.assertEqual(round_to(-1, 1, mode), -1)
        self.assertEqual(round_to(-1, -1, mode), -1)

    def test_basic_round_down(self):
        mode = RoundingMode.DOWN

        # Ties
        self.assertEqual(round_to(5.5, 1, mode), 5.0)
        self.assertEqual(round_to(5.5, -1, mode), 5.0)
        self.assertEqual(round_to(-5.5, 1, mode), -6.0)
        self.assertEqual(round_to(-5.5, -1, mode), -6.0)

        # Below tie
        self.assertEqual(round_to(5.1, 1, mode), 5.0)
        self.assertEqual(round_to(5.1, -1, mode), 5.0)
        self.assertEqual(round_to(-5.1, 1, mode), -6.0)
        self.assertEqual(round_to(-5.1, -1, mode), -6.0)

        # Above tie
        self.assertEqual(round_to(5.8, 1, mode), 5.0)
        self.assertEqual(round_to(5.8, -1, mode), 5.0)
        self.assertEqual(round_to(-5.8, 1, mode), -6.0)
        self.assertEqual(round_to(-5.8, -1, mode), -6.0)

        # Corner cases
        self.assertEqual(round_to(0, 1, mode), 0)
        self.assertEqual(round_to(0, -1, mode), 0)
        self.assertEqual(round_to(1, 1, mode), 1)
        self.assertEqual(round_to(1, -1, mode), 1)
        self.assertEqual(round_to(-1, 1, mode), -1)
        self.assertEqual(round_to(-1, -1, mode), -1)

    def test_basic_round_to_zero(self):
        mode = RoundingMode.TO_ZERO

        # Ties
        self.assertEqual(round_to(5.5, 1, mode), 5.0)
        self.assertEqual(round_to(5.5, -1, mode), 5.0)
        self.assertEqual(round_to(-5.5, 1, mode), -5.0)
        self.assertEqual(round_to(-5.5, -1, mode), -5.0)

        # Below tie
        self.assertEqual(round_to(5.1, 1, mode), 5.0)
        self.assertEqual(round_to(5.1, -1, mode), 5.0)
        self.assertEqual(round_to(-5.1, 1, mode), -5.0)
        self.assertEqual(round_to(-5.1, -1, mode), -5.0)

        # Above tie
        self.assertEqual(round_to(5.8, 1, mode), 5.0)
        self.assertEqual(round_to(5.8, -1, mode), 5.0)
        self.assertEqual(round_to(-5.8, 1, mode), -5.0)
        self.assertEqual(round_to(-5.8, -1, mode), -5.0)

        # Corner cases
        self.assertEqual(round_to(0, 1, mode), 0)
        self.assertEqual(round_to(0, -1, mode), 0)
        self.assertEqual(round_to(1, 1, mode), 1)
        self.assertEqual(round_to(1, -1, mode), 1)
        self.assertEqual(round_to(-1, 1, mode), -1)
        self.assertEqual(round_to(-1, -1, mode), -1)

    def test_basic_round_from_zero(self):
        mode = RoundingMode.FROM_ZERO

        # Ties
        self.assertEqual(round_to(5.5, 1, mode), 6.0)
        self.assertEqual(round_to(5.5, -1, mode), 6.0)
        self.assertEqual(round_to(-5.5, 1, mode), -6.0)
        self.assertEqual(round_to(-5.5, -1, mode), -6.0)

        # Below tie
        self.assertEqual(round_to(5.1, 1, mode), 6.0)
        self.assertEqual(round_to(5.1, -1, mode), 6.0)
        self.assertEqual(round_to(-5.1, 1, mode), -6.0)
        self.assertEqual(round_to(-5.1, -1, mode), -6.0)

        # Above tie
        self.assertEqual(round_to(5.8, 1, mode), 6.0)
        self.assertEqual(round_to(5.8, -1, mode), 6.0)
        self.assertEqual(round_to(-5.8, 1, mode), -6.0)
        self.assertEqual(round_to(-5.8, -1, mode), -6.0)

        # Corner cases
        self.assertEqual(round_to(0, 1, mode), 0)
        self.assertEqual(round_to(0, -1, mode), 0)
        self.assertEqual(round_to(1, 1, mode), 1)
        self.assertEqual(round_to(1, -1, mode), 1)
        self.assertEqual(round_to(-1, 1, mode), -1)
        self.assertEqual(round_to(-1, -1, mode), -1)

    def test_basic_round_nearest_ties_up(self):
        mode = RoundingMode.NEAREST_TIES_UP

        # Ties
        self.assertEqual(round_to(5.5, 1, mode), 6.0)
        self.assertEqual(round_to(5.5, -1, mode), 6.0)
        self.assertEqual(round_to(-5.5, 1, mode), -5.0)
        self.assertEqual(round_to(-5.5, -1, mode), -5.0)

        # Below tie
        self.assertEqual(round_to(5.1, 1, mode), 5.0)
        self.assertEqual(round_to(5.1, -1, mode), 5.0)
        self.assertEqual(round_to(-5.1, 1, mode), -5.0)
        self.assertEqual(round_to(-5.1, -1, mode), -5.0)

        # Above tie
        self.assertEqual(round_to(5.8, 1, mode), 6.0)
        self.assertEqual(round_to(5.8, -1, mode), 6.0)
        self.assertEqual(round_to(-5.8, 1, mode), -6.0)
        self.assertEqual(round_to(-5.8, -1, mode), -6.0)

        # Corner cases
        self.assertEqual(round_to(0, 1, mode), 0)
        self.assertEqual(round_to(0, -1, mode), 0)
        self.assertEqual(round_to(1, 1, mode), 1)
        self.assertEqual(round_to(1, -1, mode), 1)
        self.assertEqual(round_to(-1, 1, mode), -1)
        self.assertEqual(round_to(-1, -1, mode), -1)

    def test_basic_round_nearest_ties_from_zero(self):
        mode = RoundingMode.NEAREST_TIES_FROM_ZERO

        # Ties
        self.assertEqual(round_to(5.5, 1, mode), 6.0)
        self.assertEqual(round_to(5.5, -1, mode), 6.0)
        self.assertEqual(round_to(-5.5, 1, mode), -6.0)
        self.assertEqual(round_to(-5.5, -1, mode), -6.0)

        # Below tie
        self.assertEqual(round_to(5.1, 1, mode), 5.0)
        self.assertEqual(round_to(5.1, -1, mode), 5.0)
        self.assertEqual(round_to(-5.1, 1, mode), -5.0)
        self.assertEqual(round_to(-5.1, -1, mode), -5.0)

        # Above tie
        self.assertEqual(round_to(5.8, 1, mode), 6.0)
        self.assertEqual(round_to(5.8, -1, mode), 6.0)
        self.assertEqual(round_to(-5.8, 1, mode), -6.0)
        self.assertEqual(round_to(-5.8, -1, mode), -6.0)

        # Corner cases
        self.assertEqual(round_to(0, 1, mode), 0)
        self.assertEqual(round_to(0, -1, mode), 0)
        self.assertEqual(round_to(1, 1, mode), 1)
        self.assertEqual(round_to(1, -1, mode), 1)
        self.assertEqual(round_to(-1, 1, mode), -1)
        self.assertEqual(round_to(-1, -1, mode), -1)

    def test_mod_round_up(self):
        mode = RoundingMode.UP

        # Ties
        self.assertEqual(round_to(15, 10, mode), 20)
        self.assertEqual(round_to(-15, 10, mode), -10)

        # Below tie
        self.assertEqual(round_to(13, 10, mode), 20)
        self.assertEqual(round_to(-13, 10, mode), -10)

        # Above tie
        self.assertEqual(round_to(17, 10, mode), 20)
        self.assertEqual(round_to(-17, 10, mode), -10)

    def test_mod_round_down(self):
        mode = RoundingMode.DOWN

        # Ties
        self.assertEqual(round_to(15, 10, mode), 10)
        self.assertEqual(round_to(-15, 10, mode), -20)

        # Below tie
        self.assertEqual(round_to(13, 10, mode), 10)
        self.assertEqual(round_to(-13, 10, mode), -20)

        # Above tie
        self.assertEqual(round_to(17, 10, mode), 10)
        self.assertEqual(round_to(-17, 10, mode), -20)

    def test_mod_round_to_zero(self):
        mode = RoundingMode.TO_ZERO

        # Ties
        self.assertEqual(round_to(15, 10, mode), 10)
        self.assertEqual(round_to(-15, 10, mode), -10)

        # Below tie
        self.assertEqual(round_to(13, 10, mode), 10)
        self.assertEqual(round_to(-13, 10, mode), -10)

        # Above tie
        self.assertEqual(round_to(17, 10, mode), 10)
        self.assertEqual(round_to(-17, 10, mode), -10)

    def test_mod_round_from_zero(self):
        mode = RoundingMode.FROM_ZERO

        # Ties
        self.assertEqual(round_to(15, 10, mode), 20)
        self.assertEqual(round_to(-15, 10, mode), -20)

        # Below tie
        self.assertEqual(round_to(13, 10, mode), 20)
        self.assertEqual(round_to(-13, 10, mode), -20)

        # Above tie
        self.assertEqual(round_to(17, 10, mode), 20)
        self.assertEqual(round_to(-17, 10, mode), -20)

    def test_mod_round_nearest_ties_up(self):
        mode = RoundingMode.NEAREST_TIES_UP

        # Ties
        self.assertEqual(round_to(15, 10, mode), 20)
        self.assertEqual(round_to(-15, 10, mode), -10)

        # Below tie
        self.assertEqual(round_to(13, 10, mode), 10)
        self.assertEqual(round_to(-13, 10, mode), -10)

        # Above tie
        self.assertEqual(round_to(17, 10, mode), 20)
        self.assertEqual(round_to(-17, 10, mode), -20)

    def test_mod_round_nearest_ties_from_zero(self):
        mode = RoundingMode.NEAREST_TIES_FROM_ZERO

        # Ties
        self.assertEqual(round_to(15, 10, mode), 20)
        self.assertEqual(round_to(-15, 10, mode), -20)

        # Below tie
        self.assertEqual(round_to(13, 10, mode), 10)
        self.assertEqual(round_to(-13, 10, mode), -10)

        # Above tie
        self.assertEqual(round_to(17, 10, mode), 20)
        self.assertEqual(round_to(-17, 10, mode), -20)

    def test_time_round_up(self):
        mode = RoundingMode.UP

        # Ties
        self.assertEqual(round_to(30, 60, mode), 60)
        self.assertEqual(round_to(-30, 60, mode), 0)

        # Below tie
        self.assertEqual(round_to(1, 60, mode), 60)
        self.assertEqual(round_to(-1, 60, mode), 0)

        # Above tie
        self.assertEqual(round_to(59, 60, mode), 60)
        self.assertEqual(round_to(-59, 60, mode), 0)

    def test_time_round_down(self):
        mode = RoundingMode.DOWN

        # Ties
        self.assertEqual(round_to(30, 60, mode), 0)
        self.assertEqual(round_to(-30, 60, mode), -60)

        # Below tie
        self.assertEqual(round_to(1, 60, mode), 0)
        self.assertEqual(round_to(-1, 60, mode), -60)

        # Above tie
        self.assertEqual(round_to(59, 60, mode), 0)
        self.assertEqual(round_to(-59, 60, mode), -60)

    def test_time_round_to_zero(self):
        mode = RoundingMode.TO_ZERO

        # Ties
        self.assertEqual(round_to(30, 60, mode), 0)
        self.assertEqual(round_to(-30, 60, mode), 0)

        # Below tie
        self.assertEqual(round_to(1, 60, mode), 0)
        self.assertEqual(round_to(-1, 60, mode), 0)

        # Above tie
        self.assertEqual(round_to(59, 60, mode), 0)
        self.assertEqual(round_to(-59, 60, mode), 0)

    def test_time_round_from_zero(self):
        mode = RoundingMode.FROM_ZERO

        # Ties
        self.assertEqual(round_to(30, 60, mode), 60)
        self.assertEqual(round_to(-30, 60, mode), -60)

        # Below tie
        self.assertEqual(round_to(1, 60, mode), 60)
        self.assertEqual(round_to(-1, 60, mode), -60)

        # Above tie
        self.assertEqual(round_to(59, 60, mode), 60)
        self.assertEqual(round_to(-59, 60, mode), -60)

    def test_time_round_nearest_ties_from_zero(self):
        mode = RoundingMode.NEAREST_TIES_FROM_ZERO

        # Ties
        self.assertEqual(round_to(30, 60, mode), 60)
        self.assertEqual(round_to(-30, 60, mode), -60)

        # Below tie
        self.assertEqual(round_to(1, 60, mode), 0)
        self.assertEqual(round_to(-1, 60, mode), 0)

        # Above tie
        self.assertEqual(round_to(59, 60, mode), 60)
        self.assertEqual(round_to(-59, 60, mode), -60)

    def test_time_round_nearest_ties_up(self):
        mode = RoundingMode.NEAREST_TIES_UP

        # Ties
        self.assertEqual(round_to(30, 60, mode), 60)
        self.assertEqual(round_to(-30, 60, mode), 0)

        # Below tie
        self.assertEqual(round_to(1, 60, mode), 0)
        self.assertEqual(round_to(-1, 60, mode), 0)

        # Above tie
        self.assertEqual(round_to(59, 60, mode), 60)
        self.assertEqual(round_to(-59, 60, mode), -60)

class TestMathFuncs(unittest.TestCase):
    def test_mean(self):
        nums = [3, 5, 7, 8, 12]
        self.assertEqual(mathutil.mean(nums), 7)

    def test_weighted_mean(self):
        nums = [3, 7, 29]
        weights = [8, 26, 5]

        self.assertEqual(mathutil.weighted_mean(nums, weights), 9)

    def test_mean_radians(self):
        nums = [0, math.pi/2, math.pi]

        for i in range(1, 100):
            weights = [i, 999999, i]
            self.assertEqual(mathutil.angle_mean_radians(nums, weights=weights), math.pi/2)

    def test_mean_degrees(self):
        nums = [0, 90, 180]

        for i in range(1, 100):
            weights = [i, 99999, i]
            self.assertEqual(mathutil.angle_mean_degrees(nums, weights=weights), 90)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
