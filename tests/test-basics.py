#!/usr/bin/env python
import unittest
import pandas as pd
import pdfplumber
import sys, os
import six

HERE = os.path.abspath(os.path.dirname(__file__))
PDF_PATH = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")

class TestLoad(unittest.TestCase):

    def test_load(self):
        with open(PDF_PATH, "rb") as f:
            with pdfplumber.load(f) as pdf:
                assert(len(pdf.objects) > 0)

class TestBasics(unittest.TestCase):

    def setUp(self):
        self.pdf = pdfplumber.from_path(PDF_PATH)

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

    def test_within_bbox(self):
        bbox = (0, 0, 200, 200)
        original = self.pdf.pages[0]
        step_1 = original.within_bbox(bbox)
        assert(step_1.width == 200)
        assert(len(step_1.chars) < len(original.chars))

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

    def test_flush_cache(self):
        cropped = self.pdf.pages[0].crop((0, 0, 200, 200))
        assert(not hasattr(cropped, "_objects"))
        assert(len(cropped.objects) > 0)
        assert(len(cropped._objects) > 0)
        cropped.flush_cache()
        assert(not hasattr(cropped, "_objects"))

