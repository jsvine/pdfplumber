#!/usr/bin/env python
import gc
import os
import unittest
import warnings

import pdfplumber

HERE = os.path.abspath(os.path.dirname(__file__))
PATH = os.path.join(HERE, "pdfs/pdffill-demo.pdf")


class TestResourceWarning(unittest.TestCase):
    def test_no_resource_warning_with_context_manager(self):
        """Using 'with' should not emit ResourceWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with pdfplumber.open(PATH) as pdf:
                _ = pdf.pages
            assert not any(issubclass(x.category, ResourceWarning) for x in w)

    def test_no_resource_warning_without_context_manager(self):
        """Even without 'with', __del__ should close the handle cleanly."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            pdf = pdfplumber.open(PATH)
            _ = pdf.pages
            del pdf
            gc.collect()
            assert not any(issubclass(x.category, ResourceWarning) for x in w)

    def test_external_stream_not_closed(self):
        """When the caller passes a stream, pdfplumber should NOT close it."""
        with open(PATH, "rb") as f:
            pdf = pdfplumber.open(f)
            _ = pdf.pages
            del pdf
            gc.collect()
            assert not f.closed
