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
        path = os.path.join(HERE, "pdfs/Acorn_127_201604.pdf")
        test_pdf = pdfplumber.from_path(path)
        self.pdf_chars = test_pdf.pages[0].chars


    def test_fontname(self):
        extract_words(self.pdf_chars, match_fontsize=False, match_fontname=False)
        with self.assertRaises(WordFontError):
            extract_words(self.pdf_chars, match_fontsize=False)

    def test_font_height_tolerance(self):
        extract_words(self.pdf_chars, font_height_tolerance=3.5, match_fontname=False)
        with self.assertRaises(WordFontError): 
            extract_words(self.pdf_chars, font_height_tolerance=2, match_fontname=False)