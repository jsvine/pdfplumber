#!/usr/bin/env python
import logging
import os
import unittest

import pdfplumber

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
            page = pdf.pages[0]
            assert len(page.textboxhorizontals) == 27
            assert len(page.textlinehorizontals) == 79
            assert "text" in page.textboxhorizontals[0]
            assert "text" in page.textlinehorizontals[0]
            assert len(page.chars) == 4408
            assert "anno" not in page.objects.keys()

    def test_vertical_texts(self):
        path = os.path.join(HERE, "pdfs/issue-192-example.pdf")
        laparams = {"detect_vertical": True}
        with pdfplumber.open(path, laparams=laparams) as pdf:
            page = pdf.pages[0]
            assert len(page.textlinehorizontals) == 142
            assert len(page.textboxhorizontals) == 74
            assert len(page.textlineverticals) == 11
            assert len(page.textboxverticals) == 6
            assert "text" in page.textboxverticals[0]
            assert "text" in page.textlineverticals[0]

    def test_issue_383(self):
        with pdfplumber.open(self.path, laparams={}) as pdf:
            p0 = pdf.pages[0]
            assert "anno" not in p0.objects.keys()
            cropped = p0.crop((0, 0, 100, 100))
            assert len(cropped.objects)
