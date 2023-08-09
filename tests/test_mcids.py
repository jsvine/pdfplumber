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
                if not mcids[c["mcid"]]:
                    mcids[c["mcid"]] = c["tag"] + ": "
                mcids[c["mcid"]] += c["text"]
        assert mcids == [
            "Standard: Test of figures",
            "",
            "P: 1 ligne",
            "P: 2 ligne",
            "P: 3 ligne",
            "P: 4 ligne",
            "P: 0",
            "P: 2",
            "P: 4",
            "P: 6",
            "P: 8",
            "P: 10",
            "P: 12",
            "P: Figure 1: Chart",
            "",
            "P: 1 colonne",
            "P: 2 colonne",
            "P: 3 colonne",
        ]
        # Check line and curve MCIDs
        line_mcids = set(x["mcid"] for x in page.lines)
        curve_mcids = set(x["mcid"] for x in page.curves)
        assert all(x["tag"] == "Figure" for x in page.lines)
        assert all(x["tag"] == "Figure" for x in page.curves)
        assert line_mcids & {1, 14}
        assert curve_mcids & {1, 14}
        # No rects to test unfortunately!
