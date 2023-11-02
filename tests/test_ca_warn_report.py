#!/usr/bin/env python
import logging
import os
import unittest

import pdfplumber
from pdfplumber import table, utils

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


def fix_row_spaces(row):
    return [(x or "").replace(" ", "") for x in row[:3]] + row[3:]


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        self.path = os.path.join(
            HERE, "pdfs/WARN-Report-for-7-1-2015-to-03-25-2016.pdf"
        )
        self.pdf = pdfplumber.open(self.path)
        self.PDF_WIDTH = self.pdf.pages[0].width

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_page_limiting(self):
        with pdfplumber.open(self.path, pages=[1, 3]) as pdf:
            assert len(pdf.pages) == 2
            assert pdf.pages[1].page_number == 3

    def test_objects(self):
        p = self.pdf.pages[0]
        assert len(p.chars)
        assert len(p.rects)
        assert len(p.images)

    def test_parse(self):

        rect_x0_clusters = utils.cluster_list(
            [r["x0"] for r in self.pdf.pages[1].rects], tolerance=3
        )

        v_lines = [x[0] for x in rect_x0_clusters]

        def parse_page(page):
            data = page.extract_table(
                {"vertical_strategy": "explicit", "explicit_vertical_lines": v_lines}
            )
            without_spaces = [fix_row_spaces(row) for row in data]
            return without_spaces

        parsed = parse_page(self.pdf.pages[0])

        assert parsed[0] == [
            "NoticeDate",
            "Effective",
            "Received",
            "Company",
            "City",
            "No. Of",
            "Layoff/Closure",
        ]

        assert parsed[1] == [
            "06/22/2015",
            "03/25/2016",
            "07/01/2015",
            "Maxim Integrated Product",
            "San Jose",
            "150",
            "Closure Permanent",
        ]

    def test_edge_merging(self):
        p0 = self.pdf.pages[0]
        assert len(p0.edges) == 364
        assert (
            len(
                table.merge_edges(
                    p0.edges,
                    snap_x_tolerance=3,
                    snap_y_tolerance=3,
                    join_x_tolerance=3,
                    join_y_tolerance=3,
                )
            )
            == 46
        )
        assert (
            len(
                table.merge_edges(
                    p0.edges,
                    snap_x_tolerance=3,
                    snap_y_tolerance=3,
                    join_x_tolerance=3,
                    join_y_tolerance=0,
                )
            )
            == 52
        )
        assert (
            len(
                table.merge_edges(
                    p0.edges,
                    snap_x_tolerance=0,
                    snap_y_tolerance=3,
                    join_x_tolerance=3,
                    join_y_tolerance=3,
                )
            )
            == 94
        )
        assert (
            len(
                table.merge_edges(
                    p0.edges,
                    snap_x_tolerance=3,
                    snap_y_tolerance=0,
                    join_x_tolerance=3,
                    join_y_tolerance=3,
                )
            )
            == 174
        )

    def test_vertices(self):
        p0 = self.pdf.pages[0]
        edges = table.merge_edges(
            p0.edges,
            snap_x_tolerance=3,
            snap_y_tolerance=3,
            join_x_tolerance=3,
            join_y_tolerance=3,
        )
        ixs = table.edges_to_intersections(edges)
        assert len(ixs.keys()) == 304  # 38x8
