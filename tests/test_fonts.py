#!/usr/bin/env python
import unittest
import sys
import os
import logging

import pdfplumber
from pdfplumber.utils import extract_words, WordFontError

logging.disable(logging.ERROR)
HERE = os.path.abspath(os.path.dirname(__file__))

class Test(unittest.TestCase):

    def setUp(self):
        fontheight_path = os.path.join(HERE, "pdfs/fontheight_test.pdf")
        fontheight_test_pdf = pdfplumber.from_path(fontheight_path)
        self.height_chars = fontheight_test_pdf.pages[0].chars

        fontname_path = os.path.join(HERE, "pdfs/fontname_test.pdf")
        fontname_test_pdf = pdfplumber.from_path(fontname_path)
        self.font_chars = fontname_test_pdf.pages[0].chars

    def test_fontheight(self):
        # Shouldn't raise an error
        extract_words(self.height_chars, x_tolerance=1, match_fontsize=False)
        with self.assertRaises(WordFontError):
            extract_words(self.height_chars, x_tolerance=1)

    def test_fontname(self):
        # Shouldn't raise an error
        extract_words(self.font_chars, x_tolerance=1, match_fontname=False)
        with self.assertRaises(WordFontError): 
            extract_words(self.font_chars, x_tolerance=1)