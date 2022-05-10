#!/usr/bin/env python
import os
import unittest

import pdfplumber
from pdfplumber.ctm import CTM

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    def test_pdffill_demo(self):
        path = os.path.join(HERE, "pdfs/pdffill-demo.pdf")
        pdf = pdfplumber.open(path)
        left_r = pdf.pages[3].chars[97]
        right_r = pdf.pages[3].chars[105]

        left_ctm = CTM(*left_r["matrix"])
        right_ctm = CTM(*right_r["matrix"])

        assert round(left_ctm.translation_x) == 126
        assert round(right_ctm.translation_x) == 372

        assert round(left_ctm.translation_y) == 519
        assert round(right_ctm.translation_y) == 562

        assert left_ctm.skew_x == 45
        assert right_ctm.skew_x == -45

        assert left_ctm.skew_y == 45
        assert right_ctm.skew_y == -45

        assert round(left_ctm.scale_x, 3) == 1
        assert round(right_ctm.scale_x, 3) == 1

        assert round(left_ctm.scale_y, 3) == 1
        assert round(right_ctm.scale_y, 3) == 1
