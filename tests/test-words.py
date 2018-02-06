#!/usr/bin/env python
import unittest
import sys
import os
import logging
import pandas as pd

import pdfplumber
from pdfplumber.utils import extract_words

logging.disable(logging.ERROR)
HERE = os.path.abspath(os.path.dirname(__file__))

class Test(unittest.TestCase):
    """
    Tests below adapted from jsfenfen/pdfplumber. Thanks @jsfenfen!
    """
    def setUp(self):
        path = os.path.join(HERE, "pdfs/Acorn_127_201604.pdf")
        """ 
        This file has inconsistently named fonts and font sizes.
        Some words begin with characters roughly 3 (units?) bigger in size.
        Courtesy of Ryan Ross (Prince Edward Island Guardian)
        http://www.gov.pe.ca/publicdisclosure/pdSummary.php
        """
        test_pdf = pdfplumber.open(path)
        self.chars = test_pdf.pages[0].chars

        """ As of this writing, the default x_tolerance is 3, y_tolerance is 3 and default_font_height_tolerance is 1 """

        self.default_x_tolerance = 3
        self.default_y_tolerance = 3
        self.default_fontsize_tolerance = 3


    def test_match_both(self):
        words = extract_words(
                self.chars, 
                x_tolerance = self.default_x_tolerance, 
                y_tolerance = self.default_y_tolerance, 
                fontsize_tolerance = self.default_fontsize_tolerance, 
                match_fontsize = True,
                match_fontname = True
            )
        assert len(words) == 121
        assert " ".join(x["text"] for x in words[:2]) == "P E"

    def test_match_fontname(self):
        words = extract_words(
                self.chars, 
                x_tolerance = self.default_x_tolerance, 
                y_tolerance = self.default_y_tolerance, 
                fontsize_tolerance = self.default_fontsize_tolerance, 
                match_fontsize = False,
                match_fontname = True
            )
        assert len(words) == 121
        assert " ".join(x["text"] for x in words[:2]) == "P E"

    def test_match_both_custom(self):
        words = extract_words(
            self.chars, 
            x_tolerance = self.default_x_tolerance, 
            y_tolerance = 5,
            fontsize_tolerance = 6,
            match_fontsize = True, 
            match_fontname = True
        )
        assert len(words) == 117
        assert " ".join(x["text"] for x in words[:2]) == "PUBLIC EXPENSE"


    def test_match_name_custom(self):
        words = extract_words(
            self.chars, 
            x_tolerance = self.default_x_tolerance, 
            y_tolerance = 5,
            match_fontsize = False, 
            match_fontname = True
        )
        assert len(words) == 117
        assert " ".join(x["text"] for x in words[:2]) == "PUBLIC EXPENSE"

    def test_match_niether(self):
        words = extract_words(
            self.chars, 
            x_tolerance = self.default_x_tolerance, 
            y_tolerance = 5,
            match_fontsize = False, 
            match_fontname = False
        )
        assert len(words) == 116
        assert " ".join(x["text"] for x in words[:2]) == "PUBLIC EXPENSE"
