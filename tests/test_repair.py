#!/usr/bin/env python
import os
import tempfile
import unittest

import pytest

import pdfplumber

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    def test_from_issue_932(self):
        path = os.path.join(HERE, "pdfs/malformed-from-issue-932.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            char = page.chars[0]
            assert char["bottom"] > page.height

        with pdfplumber.open(path, repair=True) as pdf:
            page = pdf.pages[0]
            char = page.chars[0]
            assert char["bottom"] < page.height

        with pdfplumber.repair(path) as repaired:
            with pdfplumber.open(repaired) as pdf:
                page = pdf.pages[0]
                char = page.chars[0]
                assert char["bottom"] < page.height

    def test_other_repair_inputs(self):
        path = os.path.join(HERE, "pdfs/malformed-from-issue-932.pdf")
        with pdfplumber.open(open(path, "rb"), repair=True) as pdf:
            page = pdf.pages[0]
            char = page.chars[0]
            assert char["bottom"] < page.height

    def test_bad_repair_path(self):
        path = os.path.join(HERE, "pdfs/abc.xyz")

        with pytest.raises(Exception):
            with pdfplumber.open(path, repair=True):
                pass

    def test_repair_to_file(self):
        path = os.path.join(HERE, "pdfs/malformed-from-issue-932.pdf")
        with tempfile.NamedTemporaryFile("wb") as out:
            pdfplumber.repair(path, outfile=out.name)
            with pdfplumber.open(out.name) as pdf:
                page = pdf.pages[0]
                char = page.chars[0]
                assert char["bottom"] < page.height

    def test_repair_password(self):
        path = os.path.join(HERE, "pdfs/password-example.pdf")
        with pdfplumber.open(path, repair=True, password="test") as pdf:
            assert len(pdf.pages[0].chars)
