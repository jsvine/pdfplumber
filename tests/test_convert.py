#!/usr/bin/env python
import json
import logging
import os
import sys
import unittest
from io import StringIO
from subprocess import PIPE, Popen

import pytest

import pdfplumber

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


def run(cmd):
    return Popen(cmd, stdout=PIPE).communicate()[0]


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        self.path = os.path.join(HERE, "pdfs/pdffill-demo.pdf")
        self.pdf = pdfplumber.open(self.path, pages=[1, 2, 5])

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_json(self):
        c = json.loads(self.pdf.to_json())
        assert (
            c["pages"][0]["rects"][0]["bottom"] == self.pdf.pages[0].rects[0]["bottom"]
        )

    def test_json_attr_filter(self):
        c = json.loads(self.pdf.to_json(include_attrs=["page_number"]))
        assert list(c["pages"][0]["rects"][0].keys()) == ["object_type", "page_number"]

        with pytest.raises(ValueError):
            self.pdf.to_json(include_attrs=["page_number"], exclude_attrs=["bottom"])

        with pytest.raises(ValueError):
            self.pdf.to_json(exclude_attrs=["object_type"])

    def test_json_all_types(self):
        c = json.loads(self.pdf.to_json(object_types=None))
        found_types = c["pages"][0].keys()
        assert "chars" in found_types
        assert "lines" in found_types
        assert "rects" in found_types
        assert "images" in found_types
        assert "curves" in c["pages"][2].keys()

    def test_single_pages(self):
        c = json.loads(self.pdf.pages[0].to_json())
        assert c["rects"][0]["bottom"] == self.pdf.pages[0].rects[0]["bottom"]

    def test_additional_attr_types(self):
        path = os.path.join(HERE, "pdfs/issue-67-example.pdf")
        with pdfplumber.open(path, pages=[1]) as pdf:
            c = json.loads(pdf.to_json())
            assert len(c["pages"][0]["images"])

    def test_csv(self):
        c = self.pdf.to_csv(precision=3)
        assert c.split("\r\n")[9] == (
            "char,1,45.83,58.826,656.82,674.82,117.18,117.18,135.18,12.996,"
            '18.0,12.996,,,,,,TimesNewRomanPSMT,,,"(1, 0, 0, 1, 45.83, 660.69)"'
            ',,"(0, 0, 0)",,18.0,,,,,Y,,1,'
        )

        io = StringIO()
        self.pdf.to_csv(io, precision=3)
        io.seek(0)
        c_from_io = io.read()
        assert c == c_from_io

    def test_csv_all_types(self):
        c = self.pdf.to_csv(object_types=None)
        assert c.split("\r\n")[1].split(",")[0] == "line"

    def test_cli_json(self):
        res = run(
            [
                sys.executable,
                "-m",
                "pdfplumber.cli",
                self.path,
                "--format",
                "json",
                "--pages",
                "1-2",
                "5",
                "--indent",
                "2",
            ]
        )

        c = json.loads(res)
        assert c["pages"][0]["page_number"] == 1
        assert c["pages"][1]["page_number"] == 2
        assert c["pages"][2]["page_number"] == 5
        assert c["pages"][0]["rects"][0]["bottom"] == float(
            self.pdf.pages[0].rects[0]["bottom"]
        )

    def test_cli_csv(self):
        res = run(
            [
                sys.executable,
                "-m",
                "pdfplumber.cli",
                self.path,
                "--format",
                "csv",
                "--precision",
                "3",
            ]
        )

        assert res.decode("utf-8").split("\r\n")[9] == (
            "char,1,45.83,58.826,656.82,674.82,117.18,117.18,135.18,12.996,"
            '18.0,12.996,,,,,,TimesNewRomanPSMT,,,"(1, 0, 0, 1, 45.83, 660.69)"'
            ',,"(0, 0, 0)",,18.0,,,,,Y,,1,'
        )

    def test_cli_csv_exclude(self):
        res = run(
            [
                sys.executable,
                "-m",
                "pdfplumber.cli",
                self.path,
                "--format",
                "csv",
                "--precision",
                "3",
                "--exclude-attrs",
                "matrix",
            ]
        )

        assert res.decode("utf-8").split("\r\n")[9] == (
            "char,1,45.83,58.826,656.82,674.82,117.18,117.18,135.18,12.996,"
            "18.0,12.996,,,,,,TimesNewRomanPSMT,,"
            ',,"(0, 0, 0)",,18.0,,,,,Y,,1,'
        )

    def test_cli_csv_include(self):
        res = run(
            [
                sys.executable,
                "-m",
                "pdfplumber.cli",
                self.path,
                "--format",
                "csv",
                "--precision",
                "3",
                "--include-attrs",
                "page_number",
            ]
        )

        assert res.decode("utf-8").split("\r\n")[9] == ("char,1")

    def test_page_to_dict(self):
        x = self.pdf.pages[0].to_dict(object_types=["char"])
        assert len(x["chars"]) == len(self.pdf.pages[0].chars)
