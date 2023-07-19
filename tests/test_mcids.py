#!/usr/bin/env python3

import os
import unittest

import pdfplumber

HERE = os.path.abspath(os.path.dirname(__file__))


class TestMCIDs(unittest.TestCase):
    """Test MCID extraction."""

    def test_mcids(self):
        path = os.path.join(HERE, "pdfs/mcid_example.pdf")

        pdf = pdfplumber.open(path)
        page = pdf.pages[0]
        # Check text of MCIDS
        mcids = []
        for c in page.chars:
            if "mcid" in c:
                while len(mcids) <= c["mcid"]:
                    mcids.append("")
                mcids[c["mcid"]] += c["text"]
        assert mcids == [
            "Test of figures",
            "",
            "1 ligne",
            "2 ligne",
            "3 ligne",
            "4 ligne",
            "0",
            "2",
            "4",
            "6",
            "8",
            "10",
            "12",
            "Figure 1: Chart",
            "",
            "1 colonne",
            "2 colonne",
            "3 colonne",
        ]
        # Check line and curve MCIDs
        line_mcids = set(x["mcid"] for x in page.lines)
        curve_mcids = set(x["mcid"] for x in page.curves)
        assert line_mcids & {1, 14}
        assert curve_mcids & {1, 14}
        # No rects to test unfortunately!
