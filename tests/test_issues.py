#!/usr/bin/env python
import logging
import os
import unittest

import pdfplumber

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    def test_issue_13(self):
        """
        Test slightly simplified from gist here:
        https://github.com/jsvine/pdfplumber/issues/13
        """
        pdf = pdfplumber.open(
            os.path.join(HERE, "pdfs/issue-13-151201DSP-Fond-581-90D.pdf")
        )

        # Only find checkboxes this size
        RECT_WIDTH = 9.3
        RECT_HEIGHT = 9.3
        RECT_TOLERANCE = 2

        def filter_rects(rects):
            # Just get the rects that are the right size to be checkboxes
            rects_found = []
            for rect in rects:
                if (
                    rect["height"] > (RECT_HEIGHT - RECT_TOLERANCE)
                    and (rect["height"] < RECT_HEIGHT + RECT_TOLERANCE)
                    and (rect["width"] < RECT_WIDTH + RECT_TOLERANCE)
                    and (rect["width"] < RECT_WIDTH + RECT_TOLERANCE)
                ):
                    rects_found.append(rect)
            return rects_found

        def determine_if_checked(checkbox, checklines):
            """
            This figures out if the bounding box of (either) line used to make
            one half of the 'x' is the right size and overlaps with a rectangle.
            This isn't foolproof, but works for this case.
            It's not totally clear (to me) how common this style of checkboxes
            are used, and whether this is useful approach to them.
            Also note there should be *two* matching LTCurves for each checkbox.
            But here we only test there's at least one.
            """

            for cl in checklines:

                if (
                    checkbox["height"] > (RECT_HEIGHT - RECT_TOLERANCE)
                    and (checkbox["height"] < RECT_HEIGHT + RECT_TOLERANCE)
                    and (checkbox["width"] < RECT_WIDTH + RECT_TOLERANCE)
                    and (checkbox["width"] < RECT_WIDTH + RECT_TOLERANCE)
                ):

                    xmatch = False
                    ymatch = False

                    if max(checkbox["x0"], cl["x0"]) <= min(checkbox["x1"], cl["x1"]):
                        xmatch = True
                    if max(checkbox["y0"], cl["y0"]) <= min(checkbox["y1"], cl["y1"]):
                        ymatch = True
                    if xmatch and ymatch:
                        return True

            return False

        p0 = pdf.pages[0]
        checklines = [
            line
            for line in p0.lines
            if round(line["height"], 2) == round(line["width"], 2)
        ]  # These are diagonals
        rects = filter_rects(p0.objects["rect"])

        n_checked = sum([determine_if_checked(rect, checklines) for rect in rects])

        assert n_checked == 5
        pdf.close()

    def test_issue_14(self):
        pdf = pdfplumber.open(os.path.join(HERE, "pdfs/cupertino_usd_4-6-16.pdf"))
        assert len(pdf.objects)
        pdf.close()

    def test_issue_21(self):
        pdf = pdfplumber.open(os.path.join(HERE, "pdfs/150109DSP-Milw-505-90D.pdf"))
        assert len(pdf.objects)
        pdf.close()

    def test_issue_33(self):
        pdf = pdfplumber.open(os.path.join(HERE, "pdfs/issue-33-lorem-ipsum.pdf"))
        assert len(pdf.metadata.keys())
        pdf.close()

    def test_issue_53(self):
        pdf = pdfplumber.open(os.path.join(HERE, "pdfs/issue-53-example.pdf"))
        assert len(pdf.objects)
        pdf.close()

    def test_issue_67(self):
        pdf = pdfplumber.open(os.path.join(HERE, "pdfs/issue-67-example.pdf"))
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
            page.extract_words()

    def test_pr_136(self):
        path = os.path.join(HERE, "pdfs/pr-136-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            page.extract_words()

    def test_pr_138(self):
        path = os.path.join(HERE, "pdfs/pr-138-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            assert len(page.chars) == 5140
            page.extract_tables(
                {
                    "vertical_strategy": "explicit",
                    "horizontal_strategy": "lines",
                    "explicit_vertical_lines": page.curves + page.edges,
                }
            )

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
            assert (
                pdf.metadata["Changes"][0]["CreationDate"] == "D:20061207105020Z00'00'"
            )

    def test_issue_386(self):
        """
        util.extract_text() should not raise exception if given pure iterator
        """
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        with pdfplumber.open(path) as pdf:
            chars = (char for char in pdf.chars)
            pdfplumber.utils.extract_text(chars)

    def test_issue_463(self):
        """
        Extracting annotations should not raise UnicodeDecodeError on utf-16 text
        """
        path = os.path.join(HERE, "pdfs/issue-463-example.pdf")
        with pdfplumber.open(path) as pdf:
            annots = pdf.annots
            annots[0]["contents"] == "日本語"

    def test_issue_683(self):
        """
        Page.search ValueError: min() arg is an empty sequence

        This ultimately stemmed from a mistaken assumption in
        LayoutEngine.calculate(...) that len(char["text"]) would always equal
        1, which is not true for ligatures. Issue 683 does not provide a PDF,
        but the test PDF triggers the same error, which should now be fixed.

        Thank you to @samkit-jain for identifying and writing this test.
        """
        path = os.path.join(HERE, "pdfs/issue-71-duplicate-chars-2.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            page.search(r"\d+", regex=True)
