import logging
import unittest

from pathlib import Path
from inveniautils.pdfutil import PDFMinerTextExtractionFileWrapper
from io import BytesIO


sample_pdf_path = Path("tests") / "files" / "pdf-sample.pdf"

logging.getLogger("pdfminer").setLevel(logging.WARNING)


class TestPDFUtil(unittest.TestCase):
    def test_extract_page_text(self):
        pdf = PDFMinerTextExtractionFileWrapper(BytesIO(sample_pdf_path.read_bytes()))
        extracted_text = pdf.extract_text(page_index=0)

        expected_text = (
            "Overview - Scrapers"
            "●Download market data and store it in the “scraped data” S3 bucket"
            "●Organized hierarchically by collection and service"
            "○“collection” generally refers to a market (e.g., MISO, PJM)"
            "○“service” refers to the source of the data (e.g., a web API, an FTP ﬁle "
            "server)"
            "●Each collection contains one or more services"
            "●Each service provides one or more types of data"
            "○Fetching data for PJM alone requires accessing 6 different services\x0c"
        )
        self.assertEqual(expected_text, extracted_text)

    def test_extract_all_text(self):
        pdf = PDFMinerTextExtractionFileWrapper(BytesIO(sample_pdf_path.read_bytes()))
        extracted_text = pdf.extract_text()

        expected_text = (
            "Overview - Scrapers"
            "●Download market data and store it in the “scraped data” S3 bucket"
            "●Organized hierarchically by collection and service"
            "○“collection” generally refers to a market (e.g., MISO, PJM)"
            "○“service” refers to the source of the data (e.g., a web API, an FTP ﬁle "
            "server)"
            "●Each collection contains one or more services"
            "●Each service provides one or more types of data"
            "○Fetching data for PJM alone requires accessing 6 different services\x0c"
            "Overview - Parsers"
            "●Extract relevant information from scraped ﬁles"
            "●Convert data to a uniform format (CSV)"
            "●Parsed data is stored in the “normalized” S3 bucket"
            "●Each scraper is paired with a parser"
            "○Together a scraper and parser are referred to as a retriever\x0c"
        )
        self.assertEqual(expected_text, extracted_text)
