#!/usr/bin/env python
import unittest
import pandas as pd
import pdfplumber
from pdfplumber.utils import within_bbox, extract_columns, collate_chars
import sys, os

import logging
logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))

COLUMNS = [
    "state",
    "permit",
    "handgun",
    "long_gun",
    "other",
    "multiple",
    "admin",
    "prepawn_handgun",
    "prepawn_long_gun",
    "prepawn_other",
    "redemption_handgun",
    "redemption_long_gun",
    "redemption_other",
    "returned_handgun",
    "returned_long_gun",
    "returned_other",
    "rentals_handgun",
    "rentals_long_gun",
    "private_sale_handgun",
    "private_sale_long_gun",
    "private_sale_other",
    "return_to_seller_handgun",
    "return_to_seller_long_gun",
    "return_to_seller_other",
    "totals"
]

class Test(unittest.TestCase):

    def setUp(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        self.pdf = pdfplumber.from_path(path)
        self.PDF_WIDTH = self.pdf.pages[0].width

    def test_plain(self):
        chars = self.pdf.chars
        table_chars = within_bbox(chars, (0, 77, self.PDF_WIDTH, 485))
        table = extract_columns(table_chars, x_tolerance=2)

        def parse_value(k, x):
            if k == 0: return x
            if x == "": return None
            return int(x.replace(",", ""))

        def parse_row(row):
            return dict((COLUMNS[k], parse_value(k, v))
                for k, v in row.items())

        parsed_table = [ parse_row(row) for row in table ]

        # [1:] because first column is state name
        for c in COLUMNS[1:]:
            total = parsed_table[-1][c]
            colsum = sum(row[c] or 0 for row in parsed_table)
            assert(colsum == (total * 2))

        month_chars = within_bbox(chars, (0, 35, self.PDF_WIDTH, 65))
        month_text = collate_chars(month_chars, x_tolerance=2)
        assert(month_text == "November - 2015")

    def test_pandas(self):
        chars = pd.DataFrame(self.pdf.chars)
        table_chars = within_bbox(chars, (0, 77, self.PDF_WIDTH, 485))
        table = extract_columns(table_chars, x_tolerance=2)

        def parse_value(x):
            if pd.isnull(x): return None
            return int(x.replace(",", ""))

        table.columns = COLUMNS
        table[table.columns[1:]] = table[table.columns[1:]].applymap(parse_value)

        # [1:] because first column is state name
        for c in COLUMNS[1:]:
            total = table[c].iloc[-1]
            colsum = table[c].sum()
            assert(colsum == (total * 2))

        month_chars = within_bbox(chars, (0, 35, self.PDF_WIDTH, 65))
        month_text = collate_chars(month_chars, x_tolerance=2)
        assert(month_text == "November - 2015")
