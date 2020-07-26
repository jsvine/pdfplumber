#!/usr/bin/env python
import unittest
import pandas as pd
import pdfplumber
import sys, os
import six

import logging
logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))

class Test(unittest.TestCase):

    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        self.pdf = pdfplumber.open(path)

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_metadata(self):
        metadata = self.pdf.metadata
        assert(isinstance(metadata["Producer"], six.text_type))

    def test_pagecount(self):
        assert(len(self.pdf.pages) == 1)

    def test_page_number(self):
        assert(self.pdf.pages[0].page_number == 1)

    def test_crop_and_filter(self):
        def test(obj):
            return obj["object_type"] == "char"
        bbox = (0, 0, 200, 200)
        original = self.pdf.pages[0]
        step_1 = original.crop(bbox)
        assert(step_1.width == 200)
        assert(len(step_1.chars) < len(original.chars))
        step_2 = step_1.filter(test)
        assert(len(step_1.rects) > 0)
        assert(len(step_2.rects) == 0)

    def test_rotation(self):
        assert(self.pdf.pages[0].width == 1008)
        assert(self.pdf.pages[0].height == 612)
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11-rotated.pdf")
        with pdfplumber.open(path) as rotated:
            assert(rotated.pages[0].width == 612)
            assert(rotated.pages[0].height == 1008)

            assert(rotated.pages[0].cropbox == self.pdf.pages[0].cropbox)
            assert(rotated.pages[0].bbox != self.pdf.pages[0].bbox)

    def test_password(self):
        path = os.path.join(HERE, "pdfs/password-example.pdf")
        with pdfplumber.open(path, password = "test") as pdf:
            assert(len(pdf.chars) > 0)

    def test_colors(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        with pdfplumber.open(path) as pdf:
            rect = pdf.pages[0].rects[0]
            assert rect['non_stroking_color'] == [0.8, 1, 1]

    def test_text_colors(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        with pdfplumber.open(path) as pdf:
            char = pdf.pages[0].chars[3358]
            assert char['non_stroking_color'] == [1, 0, 0]

    def test_load_with_custom_laparams(self):
        # See https://github.com/jsvine/pdfplumber/issues/168
        path = os.path.join(HERE, "pdfs/cupertino_usd_4-6-16.pdf")
        laparams = dict(line_margin = 0.2)
        with pdfplumber.open(path, laparams = laparams) as pdf:
            assert float(pdf.pages[0].chars[0]["top"]) == 66.384
