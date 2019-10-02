import unittest
from io import BytesIO

from inveniautils.xmlutil import xml_remove_formatting, iterparse


class TestXMLUtil(unittest.TestCase):
    def test_xml_formatter(self):
        initial = "\r\n\r\n\r\n<tag1><tag2>  </tag2></tag1>                 \r\n\r\n"
        expected = b"<tag1><tag2>  </tag2></tag1>"

        self.assertEqual(xml_remove_formatting(initial), expected)

    def test_iterparse(self):
        xml = BytesIO(b"<tag1>hello there</tag1>")

        iterable = iterparse(xml, events=['end'])
        for event, element in iterable:
            self.assertEqual(element.tag, 'tag1')
            self.assertEqual(element.text, 'hello there')
