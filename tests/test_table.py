#!/usr/bin/env python
import unittest
import pytest
import pdfplumber
from pdfplumber import table
import os

import logging

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
            tf = table.TableFinder(self.pdf.pages[0], {"strategy": "x"})
            tf.get_edges()

        with pytest.raises(ValueError):
            tf = table.TableFinder(self.pdf.pages[0], {"vertical_strategy": "x"})
            tf.get_edges()

        with pytest.raises(ValueError):
            tf = table.TableFinder(
                self.pdf.pages[0],
                {
                    "vertical_strategy": "explicit",
                    "explicit_vertical_lines": [],
                },
            )

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

    def test_merge_cell(self):
        """
        See issue #420
        """
        path = os.path.join(HERE, "pdfs/issue-420-example.pdf")
        TABLE_0_0 = [
            ["Header 1", "Header 2", "Header 3", "Header 4"],
            ["Merged cell 1", "Merged cell 2", "Cell 3-1", "Cell 4-1"],
            ["Merged cell 1", "Merged cell 2", "Cell 3-2", "Cell 4-2"],
            ["Merged cell 1", "Merged cell 2", "Cell 3-2", "Cell 4-3"],
        ]
        TABLE_0_1 = [
            ["1-1", "1-1", "1-3", "1-4", "1-5", "1-6"],
            ["2-1", "2-2", "2-3", "2-4", "1-5", "1-6"],
            ["3-1", "3-2", "3-3", "3-4", "1-5", "1-6"],
            ["3-1", "4-2", "4-3", "4-3", "1-5", "1-6"],
            ["3-1", "4-2", "5-3", "5-4", "1-5", "1-6"],
            ["6-1", "4-2", "6-3", "6-4", "1-5", "1-6"],
            ["7-1", "7-1", "7-1", "7-1", "1-5", "1-6"],
            ["7-1", "7-1", "7-1", "7-1", "7-5", "1-6"],
        ]
        TABLE_1_0 = [["1", "2"], [None, "4"]]

        with pdfplumber.open(path) as pdf:
            tables = pdf.pages[0].extract_tables()
            assert len(tables) == 2
            assert TABLE_0_0 == tables[0]
            assert TABLE_0_1 == tables[1]

            tables_missing_edges = pdf.pages[1].extract_tables()
            assert len(tables_missing_edges) == 1
            assert TABLE_1_0 == tables_missing_edges[0]
