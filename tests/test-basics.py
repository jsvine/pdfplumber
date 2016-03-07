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
