import logging

import lxml.etree

logger = logging.getLogger(__name__)


class iterparse(lxml.etree.iterparse):  # noqa: N801
    def __init__(self, *args, **kwargs):
        lxml.etree.iterparse.__init__(self, *args, **kwargs)

    def __del__(self):
        # Note: It appears that clearing the root doesn't clear all
        # allocated memory.
        if self.root is not None:
            self.root.clear()


def xml_remove_formatting(content):
    try:
        import lxml.etree
    except ImportError:
        logger.warning('Unable to remove formatting from XML without lxml.')

    # http://stackoverflow.com/a/3317008/1488853
    # http://lxml.de/parsing.html#parsers
    xml_parser = lxml.etree.XMLParser(remove_blank_text=True)
    root = lxml.etree.fromstring(content, parser=xml_parser)
    return lxml.etree.tostring(root)
