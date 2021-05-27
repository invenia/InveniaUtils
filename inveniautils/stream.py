"""
Utilities related to file streams.
"""

import os
import zipfile

from gzip import GzipFile
from io import SEEK_END, BytesIO, StringIO, TextIOBase
from typing import Optional, Union, List, IO, cast

DEFAULT_SIZE = 262144  # 256KB in bytes.


def compress(stream, method="gzip", chunk_size=DEFAULT_SIZE):
    """
    Compress a stream
    """
    with AutoRewind(stream) as stream:
        if method == "gzip":
            compressed = BytesIO()

            with GzipFile(fileobj=compressed, mode="w") as temp:
                # Compress in chunks as zlib can compress via chunks.
                copy(stream, temp, chunk_size)

            compressed.seek(0)
        else:
            raise TypeError("Unknown compression method: '{}'".format(method))

    return compressed


def decompress(stream, method="gzip", chunk_size=DEFAULT_SIZE):
    """
    Decompress a stream
    """
    with AutoRewind(stream) as stream:
        if method == "gzip":
            decompressed = StringIO()

            # Copy stream to ensure we can read the content once
            # the gzip has been closed.
            with GzipFile(fileobj=stream, mode="r") as temp:
                copy(temp, decompressed, chunk_size)

            decompressed.seek(0)
        else:
            raise TypeError("Unknown compression method: '{}'".format(method))

    return decompressed


def compression_ratio(stream, method="gzip", chunk_size=DEFAULT_SIZE):
    """
    Helper method which returns the uncompressed versus compressed size.
    """
    stream.seek(0, SEEK_END)
    uncompressed_size = stream.tell()
    stream.seek(0)

    compressed = compress(stream, method, chunk_size)
    compressed.seek(0, SEEK_END)
    compressed_size = compressed.tell()

    return "{}:1".format(uncompressed_size // compressed_size)


def equal(old, new, chunk_size=DEFAULT_SIZE):
    """
    Compares the content of two file-like objects.

    Only works with seekable streams. Use equal_safe to compare
    streams that cannot be seeked.
    """
    content_equal = True

    # Note: sys.stdin fails on tell()
    old_pos = old.tell()
    old.seek(0)

    new_pos = new.tell()
    new.seek(0)

    # Note: Iterating over the stream is a bad idea since some iterators
    # iterate by lines while others iterate by a specific size.
    # Note: Using readline() could be equivalent to read(-1)!

    # Compare the streams using small chunks at a time to reduce
    # memory requirements.
    old_chunk = old.read(chunk_size)
    new_chunk = new.read(chunk_size)

    while old_chunk or new_chunk:
        if new_chunk != old_chunk:
            content_equal = False
            break

        old_chunk = old.read(chunk_size)
        new_chunk = new.read(chunk_size)

    old.seek(old_pos)
    new.seek(new_pos)

    return content_equal


def equal_safe(old, new, buffer=None, chunk_size=DEFAULT_SIZE):
    """
    Compares the content of two non-seekable file-like objects.

    Writes the content of the new stream out to the buffer so it is not
    lost.
    """
    content_equal = True

    # Note: Iterating over the stream is a bad idea since some iterators
    # iterate by lines while others iterate by a specific size.
    # Note: Using readline() could be equivalent to read(-1)!

    # Compare the streams using small chunks at a time to reduce
    # memory requirements.
    old_chunk = old.read(chunk_size)
    new_chunk = new.read(chunk_size)

    while new_chunk or (content_equal and old_chunk):
        if old_chunk != new_chunk:
            content_equal = False

        if buffer:
            buffer.write(new_chunk)

        new_chunk = new.read(chunk_size)
        old_chunk = old.read(chunk_size)

    return content_equal


class AutoRewind(object):
    def __init__(self, stream):
        self.stream = stream
        self.original_position = None

    def __enter__(self):
        self.original_position = self.stream.tell()
        self.stream.seek(0)
        return self.stream

    def __exit__(self, type, value, traceback):
        self.stream.seek(self.original_position)


def copy(input_stream, output_stream, chunk_size=DEFAULT_SIZE):
    chunk = input_stream.read(chunk_size)
    while chunk:
        if isinstance(chunk, bytes) and isinstance(output_stream, TextIOBase):
            chunk = chunk.decode()

        output_stream.write(chunk)
        chunk = input_stream.read(chunk_size)


class UnzipSingle(object):
    def __init__(self, stream):
        self.stream = stream
        self.original_position = None

    def __enter__(self):
        self.zip_file = zipfile.ZipFile(self.stream, "r")
        zipped_files = self.zip_file.namelist()

        if len(zipped_files) > 1:
            raise ValueError("Only expected one file within zip.")

        filename = zipped_files[0]
        self.content = self.zip_file.open(filename)

        # return self.content, filename
        return self.content

    def __exit__(self, type, value, traceback):
        self.content.close()
        self.zip_file.close()


class SeekableStream:
    """
    A seekable stream container for bytes or strings.
    Provides stream annotation via metadata.

    Warning: This will fully load any input streams.
    """

    def __init__(self, content: Union[str, bytes, IO] = "", **kwargs):
        if isinstance(content, str):
            self._content = StringIO(content)  # type: Union[StringIO, BytesIO]
        elif isinstance(content, bytes):
            self._content = BytesIO(content)
        elif hasattr(content, "read") and callable(content.read):
            if hasattr(content, "seekable") and content.seekable():
                content.seek(0)
            chunk = content.read(DEFAULT_SIZE)
            self._content = StringIO() if isinstance(chunk, str) else BytesIO()
            self._content.write(chunk)
            copy(content, self._content)
            self._content.seek(0)
        else:
            raise TypeError(f"Invalid content type: {type(content)}.")

        self.is_bytes = isinstance(self._content, BytesIO)
        self.metadata = kwargs

    @property
    def closed(self) -> bool:
        return self._content.closed

    def close(self):
        self._content.close()

    def seek(self, offset: int, whence: int = os.SEEK_SET):
        self._content.seek(offset, whence)

    def seekable(self) -> bool:
        return self._content.seekable()

    def tell(self) -> int:
        return self._content.tell()

    def read(self, size: int = -1) -> Union[str, bytes]:
        return self._content.read(size)

    def readline(self, size: int = -1) -> Union[str, bytes]:
        return self._content.readline(size)

    def readlines(self, hint: int = -1) -> Union[List[str], List[bytes]]:
        return self._content.readlines(hint)

    def readable(self) -> bool:
        return self._content.readable()

    def write(self, content: Union[str, bytes, bytearray]) -> int:
        if not self.is_bytes and type(content) is str:
            content = cast(str, content)
            self._content = cast(StringIO, self._content)
            return self._content.write(content)
        elif self.is_bytes and type(content) in (bytes, bytearray):
            content = cast(Union[bytes, bytearray], content)
            self._content = cast(BytesIO, self._content)
            return self._content.write(content)
        else:
            raise TypeError(
                f"Cannot write {type(content)} to {type(self._content)} stream."
            )

    def save(
        self, directory: str, filename: Optional[str] = None, overwrite: bool = False
    ):
        if filename is None:
            if "filename" in self.metadata:
                filename = self.metadata["filename"]
            else:
                raise ValueError("Specify a filename to save as.")

        path = os.path.join(directory, filename)

        if not overwrite and os.path.exists(path):
            raise IOError("File already exists. Use overwrite.")

        with AutoRewind(self._content) as input_stream:
            with open(path, "w") as output_stream:
                copy(input_stream, output_stream)

    def __next__(self) -> Union[str, bytes]:
        return self._content.__next__()

    def __iter__(self) -> "SeekableStream":
        return self
