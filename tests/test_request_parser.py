import json
import unittest
from datetime import datetime

from inveniautils.request_parser import RequestEncoder
from inveniautils.request_parser import RequestDecoder


class TestRequestEncoder(unittest.TestCase):
    def test_basic(self):
        dt = datetime(2015, 1, 1, 0)

        result = json.dumps(dt, cls=RequestEncoder)

        expected = '{"_type": "datetime", "value": "%s"}' % dt.isoformat()

        self.assertEqual(result, expected)

    def test_in_dict(self):
        dt = datetime(2014, 3, 7, 3)
        dictionary = {"testThing": "blah", "dt": dt, "otherThing": 50}

        result = json.dumps(dictionary, cls=RequestEncoder)

        expected = (
            '{"testThing": "blah", ' +
            '"dt": {"_type": "datetime", "value": "%s"}, ' % dt.isoformat() +
            '"otherThing": 50}'
        )

        self.assertEqual(result, expected)

    def no_datetimes(self):
        dictionary = {"notDatetime": 50}

        result = json.dumps(dictionary, cls=RequestEncoder)

        expected = '{"notDatetime": 50}'

        self.assertEqual(result, expected)


class TestRequestDecoder(unittest.TestCase):
    def test_basic(self):
        dt = datetime(2015, 1, 1, 0)

        encoded = '{"_type": "datetime", "value": "%s"}' % dt.isoformat()

        result = json.loads(encoded, cls=RequestDecoder)

        expected = dt

        self.assertEqual(result, expected)

    def test_in_dict(self):
        dt = datetime(2014, 3, 7, 3)
        encoded = (
            '{"otherThing": 50, "testThing": "blah", ' +
            '"dt": {"_type": "datetime", "value": "%s"}}' % dt.isoformat()
        )

        result = json.loads(encoded, cls=RequestDecoder)

        expected = {
            "testThing": "blah",
            "dt": dt,
            "otherThing": 50
        }

        self.assertEqual(result, expected)

    def no_datetimes(self):
        encoded = '{"notDatetime": 50}'

        result = json.loads(encoded, cls=RequestEncoder)

        expected = {"notDatetime": 50}

        self.assertEqual(result, expected)
