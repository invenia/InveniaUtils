from io import StringIO
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from typing import BinaryIO


class PDFMinerTextExtractionFileWrapper:
    def __init__(self, contents: BinaryIO):
        self._resource_manager = PDFResourceManager()
        self._pages = list(PDFPage.get_pages(contents))

    def extract_text(self, page_index: int = None, laparams: LAParams = None) -> str:
        """
        Extracts text from a PDF file.

        Args:
            page_index: The index of the page that text will be extracted from.
                        If None, text from all pages in the file will be extracted.
            laparams: A pdfminer LAParams object used to analyze the layout of the PDF
                      file to space out sentences and paragraphs.

        Returns:
            A string containing the extracted text.
        """

        if page_index is not None:
            if not isinstance(page_index, int):
                raise ValueError("page_index must be an integer.")

            pages = self._pages[page_index : page_index + 1]
        else:
            pages = self._pages

        with StringIO() as text_buffer:
            device = TextConverter(
                self._resource_manager, text_buffer, laparams=laparams
            )
            interpreter = PDFPageInterpreter(self._resource_manager, device)

            for page in pages:
                interpreter.process_page(page)

            return text_buffer.getvalue()

    def __len__(self) -> int:
        """Returns the number of pages in the PDF file"""
        return len(self._pages)
