#!/usr/bin/env python
import unittest
import pdfplumber
import sys, os

import logging
logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))

class Test(unittest.TestCase):

    def test_load(self):
        path = os.path.join(HERE, "pdfs/cupertino_usd_4-6-16.pdf")
        pdf = pdfplumber.from_path(path)
