import os

import pytest

import pdfplumber
from pdfplumber.pdf import Page, PDFPage
from pdfplumber.utils.exceptions import MalformedPDFException, PdfminerException

HERE = os.path.dirname(__file__)


@pytest.mark.parametrize("failure_stage", ["iteration", "construction"])
@pytest.mark.parametrize("failure_page", [1, 2])
@pytest.mark.parametrize("select_failure_page", [False, True])
def test_failed_page_loading_does_not_cache_partial_results(
    monkeypatch, failure_stage, failure_page, select_failure_page
):
    selection = [failure_page] if select_failure_page else None
    pdf = pdfplumber.open(
        os.path.join(HERE, "pdfs", "pdffill-demo.pdf"), pages=selection
    )
    try:
        original_pages = list(PDFPage.create_pages(pdf.doc))
        assert len(original_pages) >= 2
        message = "page loading failed"
        with monkeypatch.context() as patch:
            if failure_stage == "iteration":

                def failing_pages(doc):
                    for number, page in enumerate(original_pages, 1):
                        if number == failure_page:
                            raise ValueError(message)
                        yield page

                patch.setattr(PDFPage, "create_pages", failing_pages)
                error_type = PdfminerException
            else:

                def failing_page(pdf, page, page_number, **kwargs):
                    if page_number == failure_page:
                        raise RuntimeError(message)
                    return Page(pdf, page, page_number=page_number, **kwargs)

                patch.setattr("pdfplumber.pdf.Page", failing_page)
                error_type = RuntimeError

            # A failed load must not turn later accesses into a successful but
            # truncated (or empty) document.
            for _ in range(2):
                with pytest.raises(error_type, match=message):
                    _ = pdf.pages
            assert not hasattr(pdf, "_pages")

        # Once the underlying problem is gone, retry the entire selection and
        # cache only its complete result.
        pages = pdf.pages
        expected_numbers = selection or list(range(1, len(original_pages) + 1))
        assert [page.page_number for page in pages] == expected_numbers
        assert pdf.pages is pages
    finally:
        pdf.stream.close()


@pytest.mark.parametrize("filename", ["4691742750474240.pdf", "6085913544818688.pdf"])
def test_malformed_page_access_consistently_raises(filename):
    pdf = pdfplumber.open(os.path.join(HERE, "pdfs", "from-oss-fuzz", "load", filename))
    try:
        for _ in range(2):
            with pytest.raises(MalformedPDFException, match="Bounding box"):
                _ = pdf.pages
    finally:
        pdf.stream.close()
