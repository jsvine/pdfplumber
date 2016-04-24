#!/usr/bin/env python
import unittest
import pandas as pd
import pdfplumber
from pdfplumber.utils import cluster_list
import sys, os

import logging
logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))

def fix_row_spaces(row):
    return [ (x or "").replace(" ", "") for x in row[:3] ] + row[3:]

class Test(unittest.TestCase):

    def setUp(self):
        path = os.path.join(HERE, "pdfs/WARN-Report-for-7-1-2015-to-03-25-2016.pdf")
        self.pdf = pdfplumber.from_path(path)
        self.PDF_WIDTH = self.pdf.pages[0].width

    def test_pandas(self):

        rect_x0_clusters = cluster_list([ r["x0"]
            for r in self.pdf.pages[1].rects ], tolerance=3)

        v_lines = [ x[0] for x in rect_x0_clusters ]

        def parse_page(page):
            data = page.extract_table(v=v_lines)
            without_spaces = [ fix_row_spaces(row) for row in data ]
            return without_spaces

        parsed = parse_page(self.pdf.pages[0])

        assert(parsed[0] == [
            "NoticeDate",
            "Effective",
            "Received",
            "Company",
            "City",
            "No. Of",
            "Layoff/Closure",
        ])

        assert(parsed[1] == [
            "06/22/2015",
            "03/25/2016",
            "07/01/2015",
            "Maxim Integrated Product",
            "San Jose",
            "150",
            "Closure Permanent",
        ])
