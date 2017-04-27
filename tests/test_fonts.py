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
        """ 
        This file has inconsistently named fonts and font sizes.
        Some words begin with characters roughly 3 (units?) bigger in size.
        Courtesy of Ryan Ross (Prince Edward Island Guardian)
        http://www.gov.pe.ca/publicdisclosure/pdSummary.php
        """
        test_pdf = pdfplumber.from_path(path)
        self.pdf_chars = test_pdf.pages[0].chars

        """ As of this writing, the default x_tolerance is 3, y_tolerance is 3 and default_font_height_tolerance is 1 """

        self.default_x_tolerance = 3
        self.default_y_tolerance = 3
        self.default_font_height_tolerance = 1


    def test_fontname(self):
        extract_words(self.pdf_chars, 
                y_tolerance=self.default_y_tolerance, 
                x_tolerance=self.default_x_tolerance, 
                font_height_tolerance=self.default_font_height_tolerance, 
                match_fontsize=False, 
                match_fontname=False)

        with self.assertRaises(WordFontError):
            extract_words(self.pdf_chars, 
                y_tolerance=self.default_y_tolerance, 
                x_tolerance=self.default_x_tolerance, 
                font_height_tolerance=self.default_font_height_tolerance, 
                match_fontsize=False)

    def test_font_height_tolerance(self):
        extract_words(self.pdf_chars, 
                y_tolerance=self.default_y_tolerance, 
                x_tolerance=self.default_x_tolerance, 
                font_height_tolerance=3.5, 
                match_fontname=False)

        with self.assertRaises(WordFontError): 
            extract_words(self.pdf_chars, 
                y_tolerance=self.default_y_tolerance, 
                x_tolerance=self.default_x_tolerance, 
                font_height_tolerance=2, 
                match_fontname=False)

    def test_fontsize(self):

        with self.assertRaises(WordFontError):
            extract_words(self.pdf_chars, 
                y_tolerance=self.default_y_tolerance, 
                x_tolerance=self.default_x_tolerance, 
                font_height_tolerance=self.default_font_height_tolerance, 
                match_fontname=False)