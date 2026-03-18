#!/usr/bin/env python
import gc
import logging
import os
import unittest
import warnings

import pdfplumber

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))
PDF_PATH = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
PDF_NAME = os.path.basename(PDF_PATH)


class Test(unittest.TestCase):
    def test_internal_stream_no_resource_warning_after_gc(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            pdf = pdfplumber.open(PDF_PATH)
            _ = pdf.pages[0].chars[0]["text"]
            del pdf
            gc.collect()

        leaked_file_warnings = [
            w
            for w in caught
            if issubclass(w.category, ResourceWarning) and PDF_NAME in str(w.message)
        ]
        assert leaked_file_warnings == []

    def test_external_stream_is_not_closed(self):
        stream = open(PDF_PATH, "rb")
        try:
            pdf = pdfplumber.open(stream)
            _ = pdf.pages[0].chars[0]["text"]
            del pdf
            gc.collect()
            assert stream.closed is False
        finally:
            stream.close()
