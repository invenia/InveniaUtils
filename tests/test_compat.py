import unittest
from inveniautils.compat import cmp


class TestCompat(unittest.TestCase):
    def test_cmp(self):
        self.assertEqual(cmp(None, None), 0)
        self.assertEqual(cmp(None, 0), -1)
        self.assertEqual(cmp(0, None), 1)
        self.assertEqual(cmp(0, 0), 0)
