import logging
import unittest

from inveniautils.responses import split_multipart, filename

from requests.structures import CaseInsensitiveDict

from . import full_path


class Response(object):
    def __init__(self, headers=None, content=None, url=None):
        self.headers = headers if headers else CaseInsensitiveDict()
        self.content = content if content else ''
        self.url = url

    @classmethod
    def from_file(cls, filename, url=None):
        headers = CaseInsensitiveDict()
        content = ''
        in_header = True

        with open(filename, newline='') as fp:
            line = fp.readline()
            while line:
                if in_header and line == '\r\n':
                    in_header = False
                elif in_header:
                    marker = line.find(':')
                    key = line[:marker].strip()
                    value = line[marker + 1:].strip()
                    headers[key] = value
                else:
                    content += line

                line = fp.readline()

        return cls(headers, content, url)


class TestSplitMultipart(unittest.TestCase):
    def test_cmri(self):
        response = Response.from_file(full_path('cmri_multipart'))

        parts = split_multipart(response)

        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[0]), 1093)
        self.assertEqual(len(parts[1]), 1477)

    def test_not_multipart(self):
        response = Response()
        self.assertRaises(TypeError, split_multipart, (response,))

    def test_filename(self):
        response0 = Response.from_file(full_path('filename_test'), 'https://test.com/test/test.pdf')
        response1 = Response.from_file(full_path('multipart_filename_test'), 'http://dont.com/use/this.txt')

        expected0 = 'test.pdf'
        expected1 = 'this-is-the-file.pdf'

        self.assertEqual(filename(response0), expected0)
        self.assertEqual(filename(response1), expected1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
