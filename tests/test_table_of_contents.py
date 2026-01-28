"""
Test for PDF.table_of_contents and Page.table_of_contents properties
"""
import pdfplumber

def test_table_of_contents_property():
    # Path to your sample PDF (must exist)
    sample_pdf_path = "tests/pdfs/toc-sample.pdf"

    with pdfplumber.open(sample_pdf_path) as pdf:
        toc = pdf.table_of_contents

        # 1. Check the property exists and is a list
        assert isinstance(toc, list)

        # 2. If TOC entries exist, ensure they contain the right keys
        if toc:
            entry = toc[0]
            assert "title" in entry
            assert "level" in entry
            assert "page_number" in entry

        # 3. Verify the Page.table_of_contents matches PDF.table_of_contents
        assert toc == pdf.pages[0].table_of_contents
