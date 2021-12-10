#!/usr/bin/env python
import logging
import os
import unittest

import pdfplumber

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    def test_load(self):
        path = os.path.join(HERE, "pdfs/cupertino_usd_4-6-16.pdf")
        with pdfplumber.open(path) as pdf:
            assert len(pdf.metadata)
