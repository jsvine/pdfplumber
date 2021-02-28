#!/usr/bin/env python
import unittest
import pdfplumber
import os

import logging

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        self.path = os.path.join(HERE, "pdfs/issue-13-151201DSP-Fond-581-90D.pdf")

    def test_without_laparams(self):
        with pdfplumber.open(self.path, laparams=None) as pdf:
            objs = pdf.pages[0].objects
            assert "textboxhorizontal" not in objs.keys()
            assert len(objs["char"]) == 4408

    def test_with_laparams(self):
        with pdfplumber.open(self.path, laparams={}) as pdf:
            objs = pdf.pages[0].objects
            assert len(objs["textboxhorizontal"]) == 21
            assert len(objs["char"]) == 4408
