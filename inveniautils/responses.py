"""
responses contains helper functions for dealing with objects similar to
requests.models.Response.
"""

import re

from urllib.parse import urlparse


def filename(response):
    filename = None
    header_key = 'Content-Disposition'

    # Determine unquoted filename from Content-Disposition. ie:
    #   filename="hello \"world\".zip" -> hello "world".zip
    #   filename=helloworld.zip; -> helloworld.zip
    if hasattr(response, 'headers') and header_key in response.headers:
        match = re.search(
            r'filename\s*=\s*(?P<quote>[\'\"]?)(?P<filename>.*?)\1(?:;|$)',
            response.headers[header_key],
        )

        if match:
            filename = match.group('filename')

            # Unescape quotations.
            quote = match.group('quote')
            if len(quote) > 0:
                filename = filename.replace('\\' + quote, quote)

    if not filename and hasattr(response, 'url'):
        filename = urlparse(response.url).path.split('/')[-1]

    return filename


def split_multipart(response):
    """Splits up multipart responses into a list.

    Documentation regarding this topic can be found below.

    The Multipart Content-Type:
    http://www.w3.org/Protocols/rfc1341/7_2_Multipart.html
    """
    content_type = None
    content_type_data = []

    if hasattr(response, 'headers') and 'content-type' in response.headers:
        # http://www.w3.org/Protocols/rfc1341/4_Content-Type.html
        content_type_data = [
            param.strip()
            for param in response.headers['content-type'].split(';')
        ]

        # First parameter contains type/subtype.
        content_type = content_type_data[0]

        # Remove subtype component.
        content_type = content_type.split('/')[0]

    # http://www.w3.org/Protocols/rfc1341/7_2_Multipart.html
    if content_type != 'multipart':
        raise TypeError("Content-Type is not multipart")

    content_type_parameters = dict(
        re.search(r'(.*?)="(.*)"', param).groups()
        for param in content_type_data[1:]
    )

    toParse = response.content
    if isinstance(toParse, bytes):
        toParse = toParse.decode()

    # Separate content into multiple parts.
    #
    #   "The Content-Type field for multipart entities requires one
    #   parameter, "boundary", which is used to specify the
    #   encapsulation boundary. The encapsulation boundary is defined as
    #   a line consisting entirely of two hyphen characters ("-",
    #   decimal code 45) followed by the boundary parameter value from
    #   the Content-Type header field."
    #     - The Multipart Content-Type, 7.2.1 Multipart: The common syntax
    parts = re.split(
        r'\r\n--' +
        re.escape(content_type_parameters['boundary']) +
        r'(?:--)?\r\n',
        toParse,
    )

    # Removing the preamble and epiloge areas
    #
    #  "NOTE: These "preamble" and "epilogue" areas are not used because
    #  of the lack of proper typing of these parts and the lack of clear
    #  semantics for handling these areas at gateways, particularly
    #  X.400 gateways."
    #    - The Multipart Content-Type, 7.2.1 Multipart: The common syntax
    #
    parts.pop(0)  # Remove "preamble" area.
    parts.pop()   # Remove "epilogue" area.

    return parts
