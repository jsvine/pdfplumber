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
