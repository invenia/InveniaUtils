import unittest

from inveniautils.normalized_writer import float_to_decimal_str


class TestFloatToDecimalStr(unittest.TestCase):
    def test_basic(self):
        # Default rounding mode is NEAREST_TIES_FROM_ZERO

        # Ties
        self.assertEqual(float_to_decimal_str(0), "0")
        self.assertEqual(float_to_decimal_str(0.0001568627), "0.0001568627")
        self.assertEqual(float_to_decimal_str(0.2631890227), "0.2631890227")
        self.assertEqual(float_to_decimal_str(148.2382180031), "148.2382180031")
        self.assertEqual(
            float_to_decimal_str(3.92156862745098e-05), "0.0000392156862745098"
        )
        self.assertEqual(
            float_to_decimal_str(3.92156862745098e-15),
            "0.00000000000000392156862745098",
        )
        self.assertEqual(
            float_to_decimal_str(
                3.9215686274223543686478941232468798724231321867978945098e-100
            ),
            (
                "0.00000000000000000000000000000000000000000000000000000000000"
                "000000000000000000000000000000000000000039215686274223544"
            ),
        )
        self.assertEqual(
            float_to_decimal_str(42000000000000000.0), "42000000000000000.0"
        )
        self.assertEqual(
            float_to_decimal_str(42100000000000000.0), "42100000000000000.0"
        )
