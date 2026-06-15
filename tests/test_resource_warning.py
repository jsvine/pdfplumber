#!/usr/bin/env python
import gc
import os
import unittest
import warnings

import pdfplumber

HERE = os.path.abspath(os.path.dirname(__file__))
PATH = os.path.join(HERE, "pdfs/pdffill-demo.pdf")


class TestResourceWarning(unittest.TestCase):
    def _pdfplumber_warnings(self, warning_list):
        """Filter warnings to only those emitted by pdfplumber."""
        return [
            x
            for x in warning_list
            if issubclass(x.category, ResourceWarning)
            and "unclosed PDF file" in str(x.message)
        ]

    def test_no_warning_with_context_manager(self):
        """Using 'with' should not emit ResourceWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with pdfplumber.open(PATH) as pdf:
                _ = pdf.pages
            gc.collect()
            pw = self._pdfplumber_warnings(w)
            assert len(pw) == 0, f"Unexpected ResourceWarning(s): {pw}"

    def test_no_warning_with_explicit_close(self):
        """Calling close() explicitly should not emit ResourceWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            pdf = pdfplumber.open(PATH)
            _ = pdf.pages
            pdf.close()
            del pdf
            gc.collect()
            pw = self._pdfplumber_warnings(w)
            assert len(pw) == 0, f"Unexpected ResourceWarning(s): {pw}"

    def test_warning_without_close(self):
        """Forgetting to close should emit ResourceWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            pdf = pdfplumber.open(PATH)
            _ = pdf.pages
            del _, pdf
            gc.collect()
            pw = self._pdfplumber_warnings(w)
            assert len(pw) == 1
            assert "context manager" in str(pw[0].message).lower() or "close()" in str(
                pw[0].message
            )

    def test_external_stream_not_closed(self):
        """When the caller passes a stream, pdfplumber should NOT close it."""
        with open(PATH, "rb") as f:
            pdf = pdfplumber.open(f)
            _ = pdf.pages
            del pdf
            gc.collect()
            assert not f.closed

    def test_external_stream_no_warning(self):
        """External streams should not trigger ResourceWarning (caller owns them)."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with open(PATH, "rb") as f:
                pdf = pdfplumber.open(f)
                _ = pdf.pages
                del pdf
                gc.collect()
            assert len(self._pdfplumber_warnings(w)) == 0
