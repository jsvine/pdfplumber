#!/usr/bin/env python
import logging
import os
import unittest

import pdfplumber

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    def test_load_with_custom_laparams(self):
        path = os.path.join(HERE, "pdfs/cupertino_usd_4-6-16.pdf")
        laparams = dict(line_margin=0.2)
        with pdfplumber.open(path, laparams=laparams) as pdf:
            print(f"Found {len(pdf.pages)} pages")
            first_page = pdf.pages[0]
            print(first_page.chars)
