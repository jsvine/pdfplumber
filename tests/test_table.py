#!/usr/bin/env python
import logging
import os
import unittest

import pytest

import pdfplumber
from pdfplumber import table

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/pdffill-demo.pdf")
        self.pdf = pdfplumber.open(path)

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_orientation_errors(self):
        with pytest.raises(ValueError):
            table.join_edge_group([], "x")

    def test_table_settings_errors(self):
        with pytest.raises(ValueError):
            tf = table.TableFinder(self.pdf.pages[0], tuple())

        with pytest.raises(TypeError):
            tf = table.TableFinder(self.pdf.pages[0], {"strategy": "x"})
            tf.get_edges()

        with pytest.raises(ValueError):
            tf = table.TableFinder(self.pdf.pages[0], {"vertical_strategy": "x"})

        with pytest.raises(ValueError):
            tf = table.TableFinder(
                self.pdf.pages[0],
                {
                    "vertical_strategy": "explicit",
                    "explicit_vertical_lines": [],
                },
            )

        with pytest.raises(ValueError):
            tf = table.TableFinder(self.pdf.pages[0], {"join_tolerance": -1})
            tf.get_edges()

    def test_edges_strict(self):
        path = os.path.join(HERE, "pdfs/issue-140-example.pdf")
        with pdfplumber.open(path) as pdf:
            t = pdf.pages[0].extract_table(
                {
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict",
                }
            )

        assert t[-1] == [
            "",
            "0085648100300",
            "CENTRAL KMA",
            "LILYS 55% DARK CHOC BAR",
            "415",
            "$ 0.61",
            "$ 253.15",
            "0.0000",
            "",
        ]

    def test_rows_and_columns(self):
        path = os.path.join(HERE, "pdfs/issue-140-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            table = page.find_table()
            row = [page.crop(bbox).extract_text() for bbox in table.rows[0].cells]
            assert row == [
                "Line no",
                "UPC code",
                "Location",
                "Item Description",
                "Item Quantity",
                "Bill Amount",
                "Accrued Amount",
                "Handling Rate",
                "PO number",
            ]
            col = [page.crop(bbox).extract_text() for bbox in table.columns[1].cells]
            assert col == [
                "UPC code",
                "0085648100305",
                "0085648100380",
                "0085648100303",
                "0085648100300",
            ]

    def test_explicit_desc_decimalization(self):
        """
        See issue #290
        """
        tf = table.TableFinder(
            self.pdf.pages[0],
            {
                "vertical_strategy": "explicit",
                "explicit_vertical_lines": [100, 200, 300],
                "horizontal_strategy": "explicit",
                "explicit_horizontal_lines": [100, 200, 300],
            },
        )
        assert tf.tables[0].extract()

    def test_text_tolerance(self):
        path = os.path.join(HERE, "pdfs/senate-expenditures.pdf")
        with pdfplumber.open(path) as pdf:
            bbox = (70.332, 130.986, 420, 509.106)
            cropped = pdf.pages[0].crop(bbox)
            t = cropped.extract_table(
                {
                    "horizontal_strategy": "text",
                    "vertical_strategy": "text",
                    "min_words_vertical": 20,
                }
            )
            t_tol = cropped.extract_table(
                {
                    "horizontal_strategy": "text",
                    "vertical_strategy": "text",
                    "min_words_vertical": 20,
                    "text_x_tolerance": 1,
                }
            )
            t_tol_from_tables = cropped.extract_tables(
                {
                    "horizontal_strategy": "text",
                    "vertical_strategy": "text",
                    "min_words_vertical": 20,
                    "text_x_tolerance": 1,
                }
            )[0]

        assert t[-1] == [
            "DHAW20190070",
            "09/09/2019",
            "CITIBANK-TRAVELCBACARD",
            "08/12/2019",
            "08/14/2019",
        ]
        assert t_tol[-1] == [
            "DHAW20190070",
            "09/09/2019",
            "CITIBANK - TRAVEL CBA CARD",
            "08/12/2019",
            "08/14/2019",
        ]
        assert t_tol[-1] == t_tol_from_tables[-1]

    def test_text_layout(self):
        path = os.path.join(HERE, "pdfs/issue-53-example.pdf")
        with pdfplumber.open(path) as pdf:
            table = pdf.pages[0].extract_table(
                {
                    "text_layout": True,
                }
            )
            assert table[3][0] == "   FY2013   \n   FY2014   "

    def test_text_without_words(self):
        assert table.words_to_edges_h([]) == []
        assert table.words_to_edges_v([]) == []

    def test_issue_1335_explicit_outside_text_span(self):
        """
        See issue #1335.  When explicit vertical lines fall outside the
        natural x-span of text-derived horizontal edges, the corresponding
        columns must still be recovered.
        """

        class FakePage:
            def __init__(self, words, bbox=(0, 0, 600, 800)):
                self._words = words
                self.bbox = bbox
                self.edges = []

            def extract_words(self, **_kwargs):
                return self._words

        def word(text, x0, top):
            width = 8 * len(text)
            return {
                "text": text,
                "x0": x0,
                "x1": x0 + width,
                "top": top,
                "bottom": top + 12,
                "doctop": top,
                "upright": True,
                "height": 12,
                "width": width,
                "fontname": "Helvetica",
                "size": 10,
            }

        # Three rows of three columns; the last column's text is narrow
        # and ends well before the rightmost explicit vertical (x=500).
        # The leftmost explicit vertical (x=50) sits to the left of any
        # text.  Both columns must still be detected.
        rows = [
            [("Alpha", 60), ("100", 210), ("X", 360)],
            [("Beta", 60), ("200", 210), ("YY", 360)],
            [("Gamma", 60), ("300", 210), ("Z", 360)],
        ]
        words = [
            word(text, x0, 100 + 30 * row_idx)
            for row_idx, row in enumerate(rows)
            for text, x0 in row
        ]
        page = FakePage(words)
        tf = table.TableFinder(
            page,
            {
                "vertical_strategy": "explicit",
                "horizontal_strategy": "text",
                "explicit_vertical_lines": [50, 200, 350, 500],
                "intersection_tolerance": 5,
                "snap_tolerance": 3,
                "join_tolerance": 5,
            },
        )
        xs = sorted({p[0] for p in tf.intersections})
        assert xs == [50, 200, 350, 500]
        assert len(tf.tables) == 1
        # 3 data rows × 3 columns of cells must all be present.
        cell_xs_by_row = {}
        for x0, top, _x1, _bottom in tf.tables[0].cells:
            cell_xs_by_row.setdefault(top, set()).add(x0)
        full_rows = [
            top
            for top, xs_in_row in cell_xs_by_row.items()
            if {50, 200, 350}.issubset(xs_in_row)
        ]
        assert len(full_rows) >= 3

    def test_order(self):
        """
        See issue #336
        """
        path = os.path.join(HERE, "pdfs/issue-336-example.pdf")
        with pdfplumber.open(path) as pdf:
            tables = pdf.pages[0].extract_tables()
            assert len(tables) == 3
            assert len(tables[0]) == 8
            assert len(tables[1]) == 11
            assert len(tables[2]) == 2

    def test_issue_466_mixed_strategy(self):
        """
        See issue #466
        """
        path = os.path.join(HERE, "pdfs/issue-466-example.pdf")
        with pdfplumber.open(path) as pdf:
            tables = pdf.pages[0].extract_tables(
                {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 8,
                    "intersection_tolerance": 4,
                }
            )

            # The engine only extracts the tables which have drawn horizontal
            # lines.
            # For the 3 extracted tables, some common properties are expected:
            # - 4 rows
            # - 3 columns
            # - Data in last row contains the string 'last'
            for t in tables:
                assert len(t) == 4
                assert len(t[0]) == 3

                # Verify that all cell contain real data
                for cell in t[3]:
                    assert "last" in cell

    def test_discussion_539_null_value(self):
        """
        See discussion #539
        """
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            table_settings = {
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "explicit_vertical_lines": [],
                "explicit_horizontal_lines": [],
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "edge_min_length": 3,
                "min_words_vertical": 3,
                "min_words_horizontal": 1,
                "text_keep_blank_chars": False,
                "text_tolerance": 3,
                "intersection_tolerance": 3,
            }
            assert page.extract_table(table_settings)
            assert page.extract_tables(table_settings)

    def test_table_curves(self):
        # See https://github.com/jsvine/pdfplumber/discussions/808
        path = os.path.join(HERE, "pdfs/table-curves-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            assert len(page.curves)
            tables = page.extract_tables()
            assert len(tables) == 1
            t = tables[0]
            assert t[-2][-2] == "Uncommon"

            assert len(page.extract_tables({"vertical_strategy": "lines_strict"})) == 0
