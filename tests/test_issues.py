#!/usr/bin/env python
import unittest
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
        pdf = pdfplumber.open(
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
                    if ( max(checkbox['y0'], curve['y0']) <= min(checkbox['y1'], curve['y1']) ):
                        ymatch = True
                    if xmatch and ymatch:
                        return True

            return False

        p0 = pdf.pages[0]
        curves = p0.objects["curve"]
        rects = filter_rects(p0.objects["rect"])

        n_checked = sum([ determine_if_checked(rect, curves)
            for rect in rects ])

        assert(n_checked == 5)
        pdf.close()

    def test_issue_14(self):
        pdf = pdfplumber.open(
            os.path.join(HERE, "pdfs/cupertino_usd_4-6-16.pdf")
        )
        assert len(pdf.objects)
        pdf.close()

    def test_issue_21(self):
        pdf = pdfplumber.open(
            os.path.join(HERE, "pdfs/150109DSP-Milw-505-90D.pdf")
        )
        assert len(pdf.objects)
        pdf.close()

    def test_issue_33(self):
        pdf = pdfplumber.open(
            os.path.join(HERE, "pdfs/issue-33-lorem-ipsum.pdf")
        )
        assert len(pdf.metadata.keys())
        pdf.close()
        
    def test_issue_53(self):
        pdf = pdfplumber.open(
            os.path.join(HERE, "pdfs/issue-53-example.pdf")
        )
        assert len(pdf.objects)
        pdf.close()

    def test_issue_67(self):
        pdf = pdfplumber.open(
            os.path.join(HERE, "pdfs/issue-67-example.pdf")
        )
        assert len(pdf.metadata.keys())
        pdf.close()

    def test_pr_88(self):
        # via https://github.com/jsvine/pdfplumber/pull/88
        path = os.path.join(HERE, "pdfs/pr-88-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            words = page.extract_words()
            assert len(words) == 25

    def test_issue_90(self):
        path = os.path.join(HERE, "pdfs/issue-90-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            words = page.extract_words()

    def test_pr_136(self):
        path = os.path.join(HERE, "pdfs/pr-136-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            words = page.extract_words()

    def test_pr_138(self):
        path = os.path.join(HERE, "pdfs/pr-138-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            assert len(page.chars) == 5140
            page.extract_tables({
                "vertical_strategy": "explicit",
                "horizontal_strategy": "lines",
                "explicit_vertical_lines": page.curves + page.edges,
            })

    def test_issue_140(self):
        path = os.path.join(HERE, "pdfs/issue-140-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            cropped_page = page.crop((0, 0, page.width, 122))
            assert len(cropped_page.extract_table()) == 5

    def test_issue_203(self):
        path = os.path.join(HERE, "pdfs/issue-203-decimalize.pdf")
        with pdfplumber.open(path) as pdf:
            assert len(pdf.objects)

    def test_issue_216(self):
        """
        .extract_table() should return None if there's no table,
        instead of crashing
        """
        path = os.path.join(HERE, "pdfs/issue-140-example.pdf")
        with pdfplumber.open(path) as pdf:
            cropped = pdf.pages[0].crop((0, 0, 1, 1))
            assert cropped.extract_table() is None

    def test_issue_297(self):
        """
        Handle integer type metadata
        """
        path = os.path.join(HERE, "pdfs/issue-297-example.pdf")
        with pdfplumber.open(path) as pdf:
            assert isinstance(pdf.metadata["Copies"], int)

    def test_issue_316(self):
        """
        Handle invalid metadata
        """
        path = os.path.join(HERE, "pdfs/issue-316-example.pdf")
        with pdfplumber.open(path) as pdf:
            assert pdf.metadata["Changes"][0]["CreationDate"] == "D:20061207105020Z00'00'"
