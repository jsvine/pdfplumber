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

    def setUp(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        self.pdf = pdfplumber.from_path(path)

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
        rotated = pdfplumber.from_path(
            os.path.join(HERE, "pdfs/nics-background-checks-2015-11-rotated.pdf")
        )
        assert(self.pdf.pages[0].width == 1008)
        assert(self.pdf.pages[0].height == 612)

        assert(rotated.pages[0].width == 612)
        assert(rotated.pages[0].height == 1008)

        assert(rotated.pages[0].cropbox == self.pdf.pages[0].cropbox)
        assert(rotated.pages[0].bbox != self.pdf.pages[0].bbox)

    def test_password(self):
        path = os.path.join(HERE, "pdfs/password-example.pdf")
        pdf = pdfplumber.open(path, password = "test")
        assert(len(pdf.chars) > 0)
        pdf.close()
