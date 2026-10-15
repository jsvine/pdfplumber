#!/usr/bin/env python
import os
import shutil
import tempfile
import unittest
from unittest import mock

import pytest

import pdfplumber
from pdfplumber.repair import _repair

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

    def test_repair_invokes_ghostscript_with_safer(self):
        # The input document is untrusted, so Ghostscript must run under
        # `-dSAFER`. That sandbox is only the default on Ghostscript >= 9.50,
        # so it has to be requested explicitly to be safe on older builds.
        path = os.path.join(HERE, "pdfs/malformed-from-issue-932.pdf")

        captured = {}

        class FakeProc:
            returncode = 0

            def communicate(self, _input=None):
                return (b"%PDF-1.5\n%%EOF\n", b"")

        def fake_popen(args, **kwargs):
            captured["args"] = args
            return FakeProc()

        with mock.patch(
            "pdfplumber.repair.shutil.which", return_value="/usr/bin/gs"
        ), mock.patch("pdfplumber.repair.subprocess.Popen", fake_popen):
            _repair(path)

        assert "-dSAFER" in captured["args"]
