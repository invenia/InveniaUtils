import unittest
import pytz
from inveniautils.normalized_writer import NormalizedWriter
from inveniautils.datetime_range import DatetimeRange
from datetime import datetime, timedelta

utc = pytz.utc


class MyTestCase(unittest.TestCase):
    def test_encode_value_valid(self):
        values = [
            datetime(2020, 1, 2, 3, tzinfo=utc),
            timedelta(days=34),
            True,
            False,
            234234234234,
            9,
            3.14159,
            'I believe in learning on the job.',
            ('You just gestured to all of me.', 'Exactly!'),
            None
        ]

        expected = [
            '1577934000',
            '2937600.0',
            '1',
            '0',
            '234234234234',
            '9',
            '3.14159',
            'I believe in learning on the job.',
            'You just gestured to all of me.,Exactly!',
            None
        ]

        actual = [NormalizedWriter.encode_value(val) for val in values]

        for a, e in zip(actual, expected):
            self.assertEqual(a, e)

    def test_encode_value_invalid(self):
        self.assertRaises(TypeError, lambda: NormalizedWriter.encode_value({'a': 1}))

    def test_decode_value_valid(self):
        values = [
            '1577934000',
            '2937600.0',
            '1',
            '0',
            '234234234234',
            '9',
            '3.14159',
            'I believe in learning on the job.',
            'You just gestured to all of me.,Exactly!',
            ''
        ]

        types = [
            datetime,
            timedelta,
            bool,
            bool,
            int,
            int,
            float,
            str,
            tuple,
            None
        ]

        expected = [
            datetime(2020, 1, 2, 3, tzinfo=utc),
            timedelta(days=34),
            True,
            False,
            234234234234,
            9,
            3.14159,
            'I believe in learning on the job.',
            ('You just gestured to all of me.', 'Exactly!'),
            None
        ]

        actual = [NormalizedWriter.decode_value(val, typ) for val, typ in zip(values, types)]

        for act, exp in zip(actual, expected):
            self.assertEqual(act, exp)

    def test_decode_value_invalid(self):
        self.assertRaises(TypeError, lambda: NormalizedWriter.decode_value('testestset', dict))

    def test_write__csv(self):
        row = {
            'target_range': DatetimeRange(datetime(year=2020, month=10, day=11, tzinfo=utc),
                            datetime(year=2021, month=10, day=11, tzinfo=utc)),
            'testcolumn': 5,
            'test2': datetime(year=1996, month=2, day=1, tzinfo=utc),
            'pie': 3.14159,
            'tuple': ('Thank you for nothing, you useless reptile.', 'Im making outfits!')
        }

        expected = ('testcolumn,test2,pie,tuple,target_start,target_end,target_bounds'
                    '\r\n5,823132800,3.14159,"Thank you for nothing, you useless reptile.,'
                    'Im making outfits!",1602374400,1633910400,3\r\n')

        writer = NormalizedWriter()
        writer.write(row)

        text = writer.close().read()
        self.assertEqual(text, expected)
        pass
