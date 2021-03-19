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
            assert "anno" not in objs.keys()

    def test_issue_383(self):
        with pdfplumber.open(self.path, laparams={}) as pdf:
            p0 = pdf.pages[0]
            assert "anno" not in p0.objects.keys()
            cropped = p0.crop((0, 0, 100, 100))
            assert len(cropped.objects)
