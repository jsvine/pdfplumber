#!/usr/bin/env python
import unittest
import pandas as pd
import pdfplumber
from pdfplumber import table
import sys, os

import logging
logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))

class Test(unittest.TestCase):

    def test_mls(self):
        path = os.path.join(HERE, "pdfs/mls-salaries-2016.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0].process()

        def not_dollar_sign(obj):
            return (not obj["object_type"] == "char") \
                or (obj["text"] is not "$")

        filtered = page.filter(not_dollar_sign)

        TABLE_SETTINGS = {
            "vertical_edges": filtered.find_text_edges("v"),
            "horizontal_edges": filtered.find_text_edges("h"),
        }

        table = filtered.extract_table(TABLE_SETTINGS)

        rows = [ row for row in table
            if row[0] != "Club" ]

        assert rows[0] == [
            "ATL",
            "Burgos",
            "Efrain",
            "M",
            "62,508.00",
            "62,508.00"
        ]

        def money_to_float(x):
            return float(x.replace(",", ""))

        df = pd.DataFrame(rows)
        df[[4, 5]] = df[[ 4, 5 ]].applymap(money_to_float)
        assert df[4].sum() == 10814857.92
        assert df[5].sum() == 11370846.92

    def test_move_to_avg(self):
        assert table.move_to_avg([
            { "x0": 1, "x1": 1 },
            { "x0": 5, "x1": 5 }
        ], "v") == [
            { "x0": 3, "x1": 3 },
            { "x0": 3, "x1": 3 }
        ]

        assert table.move_to_avg([
            { "x0": 1, "x1": 2 },
            { "x0": 5, "x1": 6 }
        ], "v") == [
            { "x0": 3, "x1": 4 },
            { "x0": 3, "x1": 4 }
        ]

    def test_bad_move_to_avg(self):
        objs = [
            { "x0": 1, "x1": 1 },
            { "x0": 5, "x1": 5}
        ]
        with self.assertRaises(ValueError) as context:
            table.move_to_avg(objs, orientation="whoops")

    def test_bad_join_edge_group(self):
        with self.assertRaises(ValueError) as context:
            table.join_edge_group([], orientation="whoops")

    def test_misc_settings(self):
        path = os.path.join(HERE, "pdfs/mls-salaries-2016.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0].process()

        table = page.extract_table({
            "vertical_edges": page.find_text_edges("v") + [
                { "x": 10 },
                20 
            ],
            "horizontal_edges": page.find_text_edges("h") + [
                { "top": 10 },
                20
            ],
            "text_kwargs": {
                "x_tolerance": 3,
                "y_tolerance": 3 
            }
        })

    def test_empty_page(self):
        path = os.path.join(HERE, "pdfs/mls-salaries-2016.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0].process()
        page._objects = []
        page._objects_dict = {}
        table = page.extract_table({
            "vertical_edges": page.find_text_edges("v"),
            "horizontal_edges": page.find_text_edges("h"),
        })
        assert table is None
