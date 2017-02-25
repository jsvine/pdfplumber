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

    def test_issue_14(self):
        pdf = pdfplumber.from_path(
            os.path.join(HERE, "pdfs/cupertino_usd_4-6-16.pdf")
        )
        len(pdf.objects)

    def test_issue_21(self):
        pdf = pdfplumber.from_path(
            os.path.join(HERE, "pdfs/150109DSP-Milw-505-90D.pdf")
        )
        len(pdf.objects)
