#!/usr/bin/env python
import unittest
import pandas as pd
import pdfplumber
import sys, os
import six

import logging
logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))

class Test(unittest.TestCase):

    def test_issue_13(self):
        """
        Test slightly simplified from gist here: https://github.com/jsvine/pdfplumber/issues/13
        """
        pdf = pdfplumber.from_path(
            os.path.join(HERE, "pdfs/issue-13-151201DSP-Fond-581-90D.pdf")
        )

        # Only find checkboxes this size
        RECT_WIDTH = 9.3
        RECT_HEIGHT = 9.3
        RECT_TOLERANCE = 2

        def filter_rects(rects):
            ## Just get the rects that are the right size to be checkboxes
            rects_found = []
            for rect in rects:
                if ( rect['height'] > ( RECT_HEIGHT - RECT_TOLERANCE )   
                    and ( rect['height'] < RECT_HEIGHT + RECT_TOLERANCE) 
                    and ( rect['width'] < RECT_WIDTH + RECT_TOLERANCE) 
                    and ( rect['width'] < RECT_WIDTH + RECT_TOLERANCE) ):
                    rects_found.append(rect)
            return rects_found

        def determine_if_checked(checkbox, curve_list):
            # This figures out if the bounding box of (either) line used to make
            # one half of the 'x' is the right size and overlaps with a rectangle.
            # This isn't foolproof, but works for this case. 
            # It's not totally clear (to me) how common this style of checkboxes
            # are used, and whether this is useful approach to them.
            # Also note there should be *two* matching LTCurves for each checkbox.
            # But here we only test there's at least one. 

            for curve in curve_list:

                if ( checkbox['height'] > ( RECT_HEIGHT - RECT_TOLERANCE )   
                    and ( checkbox['height'] < RECT_HEIGHT + RECT_TOLERANCE) 
                    and ( checkbox['width'] < RECT_WIDTH + RECT_TOLERANCE) 
                    and ( checkbox['width'] < RECT_WIDTH + RECT_TOLERANCE) ):

                    xmatch = False
                    ymatch = False

                    if ( max(checkbox['x0'], curve['x0']) <= min(checkbox['x1'], curve['x1']) ):
                        xmatch = True
                    if ( max(checkbox['top'], curve['top']) <= min(checkbox['bottom'], curve['bottom']) ):
                        ymatch = True
                    if xmatch and ymatch:
                        return True

            return False

        p0 = pdf.pages[0]
        curves = p0.curves
        rects = filter_rects(p0.rects)

        n_checked = sum([ determine_if_checked(rect, curves)
            for rect in rects ])

        assert(n_checked == 5)

    def test_issue_14(self):
        pdf = pdfplumber.from_path(
            os.path.join(HERE, "pdfs/cupertino_usd_4-6-16.pdf")
        )
        assert len(pdf.objects)

    def test_issue_21(self):
        pdf = pdfplumber.from_path(
            os.path.join(HERE, "pdfs/150109DSP-Milw-505-90D.pdf")
        )
        assert len(pdf.objects)

    def test_issue_33(self):
        pdf = pdfplumber.from_path(
            os.path.join(HERE, "pdfs/issue-33-lorem-ipsum.pdf")
        )
        assert len(pdf.metadata.keys())
        
