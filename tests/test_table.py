#!/usr/bin/env python
import unittest
import pytest
import pdfplumber
from pdfplumber import table
import sys, os

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
            tf = table.TableFinder(self.pdf, { "strategy": "x" })
            td.get_edges()

        with pytest.raises(ValueError):
            tf = table.TableFinder(self.pdf, { "vertical_strategy": "x" })
            td.get_edges()

        with pytest.raises(ValueError):
            tf = table.TableFinder(self.pdf, {
                "vertical_strategy": "explicit",
                "explicit_vertical_lines": [],
            })

    def test_edges_strict(self):
        path = os.path.join(HERE, "pdfs/issue-140-example.pdf")
        with pdfplumber.open(path) as pdf:
            t = pdf.pages[0].extract_table({
                "vertical_strategy": "lines_strict",
                "horizontal_strategy": "lines_strict"
            })

        assert t[-1] == [
            "",
            "0085648100300",
            "CENTRAL KMA",
            "LILYS 55% DARK CHOC BAR",
            "415",
            "$ 0.61",
            "$ 253.15",
            "0.0000",
            ""
        ]

    def test_explicit_desc_decimalization(self):
        """
        See issue #290
        """
        tf = table.TableFinder(self.pdf.pages[0], {
            "vertical_strategy": "explicit",
            "explicit_vertical_lines": [ 100, 200, 300 ],
            "horizontal_strategy": "explicit",
            "explicit_horizontal_lines": [ 100, 200, 300 ],
        })
        assert tf.tables[0].extract()

    def test_text_without_words(self):
        assert table.words_to_edges_h([]) == []
        assert table.words_to_edges_v([]) == []
