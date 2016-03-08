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

    def test_crop_and_filter(self):
        def test(obj):
            return obj["object_type"] == "char"
        bbox = (0, 0, 200, 200)
        original = self.pdf.pages[0]
        step_1 = original.crop(bbox)
        step_2 = step_1.filter(test)
        step_3 = step_2.crop(bbox)
