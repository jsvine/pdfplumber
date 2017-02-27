#!/usr/bin/env python
import unittest
import pandas as pd
import pdfplumber
import sys, os

import logging
logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))

class Test(unittest.TestCase):

    def setUp(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        self.pdf = pdfplumber.open(path)
        self.im = self.pdf.pages[0].to_image()

    def test_basic_conversion(self):
        self.im.reset()
        self.im.draw_rect(self.im.page.rects[0])
        self.im.draw_circle(self.im.page.chars[0])
        self.im.draw_line(self.im.page.edges[0])

    def test_debug_tablefinder(self):
        self.im.reset()
        settings = {
            "horizontal_strategy": "text",
            "intersection_tolerance": 5
        }
        self.im.debug_tablefinder(settings)

    def test_curves(self):
        path = os.path.join(
            HERE,
            "../examples/pdfs/ag-energy-round-up-2017-02-24.pdf"
        )
        page = pdfplumber.open(path).pages[0]
        im = page.to_image()
        im.draw_lines(page.curves)
