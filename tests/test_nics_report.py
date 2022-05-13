#!/usr/bin/env python
import logging
import os
import unittest
from operator import itemgetter

import pdfplumber
from pdfplumber.utils import extract_text, within_bbox

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
    "totals",
]


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        self.pdf = pdfplumber.open(path)
        self.PDF_WIDTH = self.pdf.pages[0].width

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_edges(self):
        assert len(self.pdf.vertical_edges) == 700
        assert len(self.pdf.horizontal_edges) == 508

    def test_plain(self):
        page = self.pdf.pages[0]
        cropped = page.crop((0, 80, self.PDF_WIDTH, 485))
        table = cropped.extract_table(
            {
                "horizontal_strategy": "text",
                "explicit_vertical_lines": [min(map(itemgetter("x0"), cropped.chars))],
                "intersection_tolerance": 5,
            }
        )

        def parse_value(k, x):
            if k == 0:
                return x
            if x in (None, ""):
                return None
            return int(x.replace(",", ""))

        def parse_row(row):
            return dict((COLUMNS[i], parse_value(i, v)) for i, v in enumerate(row))

        parsed_table = [parse_row(row) for row in table]

        # [1:] because first column is state name
        for c in COLUMNS[1:]:
            total = parsed_table[-1][c]
            colsum = sum(row[c] or 0 for row in parsed_table)
            assert colsum == (total * 2)

        month_chars = within_bbox(page.chars, (0, 35, self.PDF_WIDTH, 65))
        month_text = extract_text(month_chars)
        assert month_text == "November - 2015"

    def test_filter(self):
        page = self.pdf.pages[0]

        def test(obj):
            if obj["object_type"] == "char":
                if obj["size"] < 15:
                    return False
            return True

        filtered = page.filter(test)
        text = filtered.extract_text()
        assert text == "NICS Firearm Background Checks\nNovember - 2015"

    def test_text_only_strategy(self):
        cropped = self.pdf.pages[0].crop((0, 80, self.PDF_WIDTH, 475))
        table = cropped.extract_table(
            dict(
                horizontal_strategy="text",
                vertical_strategy="text",
            )
        )
        assert table[0][0] == "Alabama"
        assert table[0][22] == "71,137"
        assert table[-1][0] == "Wyoming"
        assert table[-1][22] == "5,017"

    def test_explicit_horizontal(self):
        cropped = self.pdf.pages[0].crop((0, 80, self.PDF_WIDTH, 475))
        table = cropped.find_tables(
            dict(
                horizontal_strategy="text",
                vertical_strategy="text",
            )
        )[0]

        h_positions = [row.cells[0][1] for row in table.rows] + [
            table.rows[-1].cells[0][3]
        ]

        t_explicit = cropped.find_tables(
            dict(
                horizontal_strategy="explicit",
                vertical_strategy="text",
                explicit_horizontal_lines=h_positions,
            )
        )[0]

        assert table.extract() == t_explicit.extract()

        h_objs = [
            {
                "x0": 0,
                "x1": self.PDF_WIDTH,
                "width": self.PDF_WIDTH,
                "top": h,
                "bottom": h,
                "object_type": "line",
            }
            for h in h_positions
        ]

        t_explicit_objs = cropped.find_tables(
            dict(
                horizontal_strategy="explicit",
                vertical_strategy="text",
                explicit_horizontal_lines=h_objs,
            )
        )[0]

        assert table.extract() == t_explicit_objs.extract()
