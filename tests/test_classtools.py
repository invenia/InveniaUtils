import unittest
from inveniautils.classtools import full_class_name

class TestClassTools(unittest.TestCase):
    def test_classtools(self):
        print(full_class_name(self))
        self.assertEqual(full_class_name(self), "tests.test_classtools.TestClassTools")
