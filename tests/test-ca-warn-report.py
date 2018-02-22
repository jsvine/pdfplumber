#!/usr/bin/env python
import unittest
import pandas as pd
import pdfplumber
from pdfplumber import (
    utils,
    table,
    edge_finders
)
import sys, os

import logging
logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))

def fix_row_spaces(row):
    return [ (x or "").replace(" ", "") for x in row[:3] ] + row[3:]

class Test(unittest.TestCase):

    def setUp(self):
        path = os.path.join(HERE, "pdfs/WARN-Report-for-7-1-2015-to-03-25-2016.pdf")
        self.pdf = pdfplumber.from_path(path, pages=[1])
        self.PDF_WIDTH = self.pdf.pages[0].width

    def test_pandas(self):

        rect_x0_clusters = utils.cluster_list([ r["x0"]
            for r in self.pdf.pages[0].rects ], tolerance=3)

        v_lines = [ x[0] for x in rect_x0_clusters ]

        def parse_page(page):
            data = page.extract_table({
                "vertical_edges": v_lines,
                "horizontal_edges": page.horizontal_edges
            })
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

    def test_edge_merging(self):
        p0 = self.pdf.pages[0]
        assert(len(p0.edges) == 364) 
        assert(len(table.merge_edges(
            p0.edges,
            snap_x_tolerance=3,
            snap_y_tolerance=3,
            join_tolerance=3
        )) == 46)

    def test_vertices(self):
        p0 = self.pdf.pages[0]
        edges = table.merge_edges(
            p0.edges,
            snap_x_tolerance=3,
            snap_y_tolerance=3,
            join_tolerance=3
        )
        ixs = table.edges_to_intersections(edges)
        assert(len(ixs.keys()) == 304) # 38x8

    def test_image(self):
        assert(len(self.pdf.pages[0].images) == 1)

    def test_edges(self):
        v = self.pdf.pages[0].vertical_edges
        h = self.pdf.pages[0].horizontal_edges
        assert(len(v) > 0)
        assert(len(h) > 0)
        assert(len(v) + len(h) == len(self.pdf.pages[0].edges))

    def test_extract_tables(self):
        tables = self.pdf.pages[0].extract_tables()
        table = tables[0]
        assert(table[0] == [
            "Notice Date",
            "Effective",
            "Received",
            "Company",
            "City",
            "No. Of",
            "Layoff/Closure",
        ])

