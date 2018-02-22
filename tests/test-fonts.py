#!/usr/bin/env python
import unittest
import pdfplumber
import sys, os

HERE = os.path.abspath(os.path.dirname(__file__))
PDF_PATH = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
PDF = pdfplumber.open(PDF_PATH)

class TestFonts(unittest.TestCase):
    def test_font_count(self):
        assert(type(PDF.fonts) == dict)
        assert(len(PDF.fonts) == 4)
    
