import unittest
import re

from inveniautils.version import get_version_number


class TestVersions(unittest.TestCase):
    # Make sure version matches SemVar
    def test_version_string(self):
        # Regex found here: https://github.com/k-bx/python-semver/blob/master/semver.py
        regex = (
            r"^(?P<major>(?:0|[1-9][0-9]*))\."
            r"(?P<minor>(?:0|[1-9][0-9]*))\."
            r"(?P<patch>(?:0|[1-9][0-9]*))"
            r"(\-(?P<prerelease>(?:0|[1-9A-Za-z-][0-9A-Za-z-]*)"
            r"(\.(?:0|[1-9A-Za-z-][0-9A-Za-z-]*))*))?"
            r"(\+(?P<build>[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$"
        )
        self.assertTrue(re.search(regex, get_version_number()) is not None)
