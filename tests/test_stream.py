import logging
import unittest
from . import full_path

from inveniautils.stream import (
    compress,
    decompress,
    equal,
    equal_safe,
    compression_ratio,
    UnzipSingle,
    SeekableStream,
)

from io import StringIO, BytesIO


class TestCompression(unittest.TestCase):
    """
    Test the compression module.
    """

    def test_decompress_uncompressed_data(self):
        """
        Test decompression on an uncompressed stream.
        """
        uncompressed = BytesIO(b"stream")
        self.assertRaises(IOError, decompress, uncompressed)

    def test_decompress_gzip(self):
        """
        Test gzip decompression.
        """
        empty = {
            "uncompressed": "",
            "compressed": BytesIO(
                b"\x1f\x8b\x08\x00\x13\x0b\xa3S\x02\xff\x03\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00"
            ),
        }

        text = {
            "uncompressed": "foo bar baz",
            "compressed": BytesIO(
                b"\x1f\x8b\x08\x00\xa3\t\xa3S\x02\xffK\xcb\xcfWHJ,\x02"
                b"\xe2*\x00a\xdeb\xf2\x0b\x00\x00\x00"
            ),
        }

        for content, compressed in (
            (d["uncompressed"], d["compressed"]) for d in (empty, text)
        ):
            # Move file pointer to ensure that decompress works on the
            # entire stream.
            compressed.seek(3)
            stream = decompress(compressed)

            # Ensure the original position is retained.
            self.assertEqual(compressed.tell(), 3)
            self.assertEqual(stream.tell(), 0)

            self.assertEqual(stream.read(), content)

    def test_compress_none(self):
        """
        Test compression method "None".
        """
        content = "yellow bananas are delicious"
        uncompressed = BytesIO(content.encode())
        uncompressed.seek(3)

        self.assertRaises(TypeError, compress, uncompressed, method=None)

        # Compress should return the file pointer back to its original
        # position even if an exception occurs.
        self.assertEqual(uncompressed.tell(), 3)

    def test_compress_gzip_empty(self):
        """
        Test gzip compression on empty data.
        """
        content = ""
        uncompressed = BytesIO(content.encode())
        compressed = compress(uncompressed)

        # Compress should return the file pointer back to its original
        # position.
        self.assertEqual(uncompressed.tell(), 0)
        self.assertEqual(compressed.tell(), 0)

        # Check the content of the various data streams.
        self.assertEqual(uncompressed.read().decode(), content)
        self.assertNotEqual(compressed.read(), content)
        self.assertEqual(decompress(compressed).read(), content)

    def test_compress_gzip_non_empty(self):
        """
        Test gzip compression on non-empty data.
        """
        content = "foo bar baz"
        uncompressed = BytesIO(content.encode())
        compressed = compress(uncompressed)

        # Compress should return the file pointer back to its original
        # position.
        self.assertEqual(uncompressed.tell(), 0)
        self.assertEqual(compressed.tell(), 0)

        # Check the content of the various data streams.
        self.assertEqual(uncompressed.read().decode(), content)
        self.assertNotEqual(compressed.read(), content)
        self.assertEqual(decompress(compressed).read(), content)

    def test_compression_actually_compresses(self):
        streams = [BytesIO(b"a" * 100), BytesIO(b"a" * 200), BytesIO(b"a" * 400)]
        streams = [compression_ratio(stream) for stream in streams]

        expected = ["4:1", "8:1", "15:1"]

        for act, exp in zip(streams, expected):
            self.assertEqual(act, exp)

    def test_unzip_single_valid(self):
        content = b"a"
        with open(full_path("test.zip"), "rb") as stream:
            with UnzipSingle(stream) as actual:
                self.assertEqual(actual.read(), content)

    def test_unzip_single_invalid(self):
        test = UnzipSingle(open(full_path("invalidzip.zip"), "rb"))
        self.assertRaises(ValueError, lambda: test.__enter__())


class TestEqual(unittest.TestCase):
    def test_empty(self):
        self.assertRaises(AttributeError, equal, None, None, chunk_size=1)

        result = equal(StringIO(), StringIO(), chunk_size=1)
        self.assertEqual(result, True)

    def test_equal(self):
        old = StringIO("hello world")
        new = StringIO("hello world")
        expected = True

        result = equal(old, new, chunk_size=1)
        self.assertEqual(result, expected)
        self.assertEqual(old.tell(), 0)
        self.assertEqual(new.tell(), 0)

    def test_unequal(self):
        old = StringIO("hello world")
        new = StringIO("HELLO WORLD")
        expected = False

        result = equal(old, new, chunk_size=1)
        self.assertEqual(result, expected)
        self.assertEqual(old.tell(), 0)
        self.assertEqual(new.tell(), 0)

    def test_length_diff(self):
        longer = StringIO("hello world")
        shorter = StringIO("hello")
        expected = False

        result = equal(longer, shorter, chunk_size=1)
        self.assertEqual(result, expected)
        self.assertEqual(shorter.tell(), 0)
        self.assertEqual(longer.tell(), 0)

        result = equal(shorter, longer, chunk_size=1)
        self.assertEqual(result, expected)
        self.assertEqual(shorter.tell(), 0)
        self.assertEqual(longer.tell(), 0)


class TestEqualSafe(unittest.TestCase):
    def test_empty(self):
        out = StringIO()

        self.assertRaises(AttributeError, equal_safe, None, None, out, chunk_size=1)

        result = equal_safe(StringIO(), StringIO(), out, chunk_size=1)
        self.assertEqual(result, True)
        self.assertEqual(out.getvalue(), "")

    def test_equal(self):
        old = StringIO("hello world")
        new = StringIO("hello world")
        out = StringIO()
        expected = True

        result = equal_safe(old, new, out, chunk_size=1)
        self.assertEqual(result, expected)
        self.assertEqual(out.getvalue(), new.getvalue())

    def test_unequal(self):
        old = StringIO("hello world")
        new = StringIO("HELLO WORLD")
        out = StringIO()
        expected = False

        result = equal_safe(old, new, out, chunk_size=1)
        self.assertEqual(result, expected)
        self.assertEqual(out.getvalue(), new.getvalue())

    def test_length_diff(self):
        longer = StringIO("hello world")
        shorter = StringIO("hello")
        out = StringIO()
        expected = False

        result = equal_safe(longer, shorter, out, chunk_size=1)
        self.assertEqual(result, expected)
        self.assertEqual(out.getvalue(), shorter.getvalue())

        # Prepare for the next test.
        shorter.seek(0)
        longer.seek(0)
        out = StringIO()

        result = equal_safe(shorter, longer, out, chunk_size=1)
        self.assertEqual(result, expected)
        self.assertEqual(out.getvalue(), longer.getvalue())


class TestSeekableStream(unittest.TestCase):
    def test_string(self):
        input_string = "Hello World.\nI am Invenia.\nI am -50 degrees.\n"

        stream = SeekableStream(input_string)
        self.assertFalse(stream.is_bytes)

        self.assertTrue(stream.readable())
        self.assertTrue(stream.seekable())
        self.assertFalse(stream.closed)

        # test read, seek, tell
        self.assertTrue(stream.tell() == 0)
        self.assertEqual(stream.read(), input_string)
        self.assertTrue(stream.tell() == len(input_string))
        stream.seek(0)
        self.assertTrue(stream.tell() == 0)
        self.assertEqual(stream.read(25), input_string[:25])
        self.assertTrue(stream.tell() == 25)
        self.assertEqual(stream.read(), input_string[25:])
        stream.seek(25)
        self.assertEqual(stream.read(), input_string[25:])
        self.assertTrue(stream.tell() == len(input_string))

        # test readline
        stream.seek(0)
        self.assertEqual(stream.readline(), "Hello World.\n")
        self.assertEqual(stream.readline(), "I am Invenia.\n")
        self.assertEqual(stream.readline(), "I am -50 degrees.\n")
        self.assertEqual(stream.readline(), "")

        # test readlines
        stream.seek(0)
        self.assertEqual(
            stream.readlines(),
            ["Hello World.\n", "I am Invenia.\n", "I am -50 degrees.\n"],
        )
        self.assertEqual(stream.readlines(), [])

        # test iter & next
        stream.seek(0)
        it = iter(stream)
        self.assertEqual(next(it), "Hello World.\n")
        self.assertEqual(next(it), "I am Invenia.\n")
        self.assertEqual(next(it), "I am -50 degrees.\n")
        self.assertRaises(StopIteration, next, it)

        # test close
        self.assertFalse(stream.closed)
        stream.close()
        self.assertTrue(stream.closed)

    def test_read_only_byte_stream(self):
        class ReadOnly:
            def __init__(self, bytes):
                self._stream = BytesIO(bytes)

            def read(self, size: int = -1) -> bytes:
                return self._stream.read(size)

        # create a read-only stream
        input_bytes = b"Hello World.\nI am Invenia.\nI am -50 degrees.\n"
        read_stream = ReadOnly(input_bytes)
        self.assertFalse(hasattr(read_stream, "seek"))

        stream = SeekableStream(read_stream)
        self.assertTrue(stream.is_bytes)

        self.assertTrue(stream.readable())
        self.assertTrue(stream.seekable())
        self.assertFalse(stream.closed)

        # test read, seek, tell
        self.assertTrue(stream.tell() == 0)
        self.assertEqual(stream.read(), input_bytes)
        self.assertTrue(stream.tell() == len(input_bytes))
        stream.seek(0)
        self.assertTrue(stream.tell() == 0)
        self.assertEqual(stream.read(25), input_bytes[:25])
        self.assertTrue(stream.tell() == 25)
        self.assertEqual(stream.read(), input_bytes[25:])
        stream.seek(25)
        self.assertEqual(stream.read(), input_bytes[25:])
        self.assertTrue(stream.tell() == len(input_bytes))

        # test readline
        stream.seek(0)
        self.assertEqual(stream.readline(), b"Hello World.\n")
        self.assertEqual(stream.readline(), b"I am Invenia.\n")
        self.assertEqual(stream.readline(), b"I am -50 degrees.\n")
        self.assertEqual(stream.readline(), b"")

        # test readlines
        stream.seek(0)
        self.assertEqual(
            stream.readlines(),
            [b"Hello World.\n", b"I am Invenia.\n", b"I am -50 degrees.\n"],
        )
        self.assertEqual(stream.readlines(), [])

        # test iter & next
        stream.seek(0)
        it = iter(stream)
        self.assertEqual(next(it), b"Hello World.\n")
        self.assertEqual(next(it), b"I am Invenia.\n")
        self.assertEqual(next(it), b"I am -50 degrees.\n")
        self.assertRaises(StopIteration, next, it)

        # test close
        self.assertFalse(stream.closed)
        stream.close()
        self.assertTrue(stream.closed)

    def test_annotation(self):
        input_string = "Hello World.\nI am Invenia.\nI am -50 degrees.\n"

        metadata = {
            "file_name": "somefile.txt",
            "file_type": "some type",
            "some_metadata": "metadata1",
        }

        stream = SeekableStream(input_string, **metadata)
        self.assertEqual(stream.metadata, metadata)

        # update metadata
        stream.metadata["some_metadata"] = "metadata2"
        self.assertNotEqual(stream.metadata, metadata)
        metadata["some_metadata"] = "metadata2"
        self.assertEqual(stream.metadata, metadata)

        # add metadata
        stream.metadata["some_more_metadata"] = "metadata3"
        self.assertNotEqual(stream.metadata, metadata)
        metadata["some_more_metadata"] = "metadata3"
        self.assertEqual(stream.metadata, metadata)

        # delete metadata
        stream.metadata.pop("some_more_metadata")
        self.assertNotEqual(stream.metadata, metadata)
        metadata.pop("some_more_metadata")
        self.assertEqual(stream.metadata, metadata)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
