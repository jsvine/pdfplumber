#!/usr/bin/env python
import os
import shutil
import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch

import pytest

import pdfplumber

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    def test_repair_failure_diagnostics(self):
        diagnostics = [
            (b"Ghostscript: invalid input \xae", "Ghostscript: invalid input \ufffd"),
            ("Ghostscript: \u00e9chec".encode("utf-8"), "Ghostscript: \u00e9chec"),
        ]
        for stderr, expected in diagnostics:
            with self.subTest(stderr=stderr):
                with patch("subprocess.Popen") as popen:
                    popen.return_value.returncode = 1
                    popen.return_value.communicate.return_value = (b"", stderr)
                    with pytest.raises(Exception) as exc:
                        pdfplumber.repair(BytesIO(b"input"), gs_path="ghostscript")
                assert type(exc.value) is Exception
                assert str(exc.value) == expected

    def test_repair_success_with_non_utf8_diagnostics(self):
        with patch("subprocess.Popen") as popen:
            popen.return_value.returncode = 0
            popen.return_value.communicate.return_value = (
                b"repaired PDF bytes",
                b"Ghostscript warning \xae",
            )
            with pdfplumber.repair(BytesIO(b"input"), gs_path="ghostscript") as result:
                assert result.read() == b"repaired PDF bytes"

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

    def test_repair_setting(self):
        path = os.path.join(HERE, "pdfs/malformed-from-issue-932.pdf")
        with tempfile.NamedTemporaryFile("wb") as out:
            pdfplumber.repair(path, outfile=out.name)

        with tempfile.NamedTemporaryFile("wb") as out:
            pdfplumber.repair(path, outfile=out.name, setting="prepress")

    def test_repair_password(self):
        path = os.path.join(HERE, "pdfs/password-example.pdf")
        with pdfplumber.open(path, repair=True, password="test") as pdf:
            assert len(pdf.pages[0].chars)

    def test_repair_custom_path(self):
        path = os.path.join(HERE, "pdfs/malformed-from-issue-932.pdf")
        with pdfplumber.open(path, repair=True, gs_path=shutil.which("gs")) as pdf:
            assert len(pdf.pages[0].chars)
