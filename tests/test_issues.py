#!/usr/bin/env python
import logging
import os
import re

try:
    import resource
except ModuleNotFoundError:
    resource = None
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

    def test_issue_461_and_842(self):
        """
        pdfplumber should gracefully handle characters with byte-encoded
        font names.
        """
        before = b"RGJSAP+\xcb\xce\xcc\xe5"
        after = pdfplumber.page.fix_fontname_bytes(before)
        assert after == "RGJSAP+SimSun,Regular"

        before = b"\xcb\xce\xcc\xe5"
        after = pdfplumber.page.fix_fontname_bytes(before)
        assert after == "SimSun,Regular"

        path = os.path.join(HERE, "pdfs/issue-461-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            assert all(isinstance(c["fontname"], str) for c in page.chars)
            page.dedupe_chars()

        path = os.path.join(HERE, "pdfs/issue-842-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            assert all(isinstance(c["fontname"], str) for c in page.chars)
            page.dedupe_chars()

    def test_issue_463(self):
        """
        Extracting annotations should not raise UnicodeDecodeError on utf-16 text
        """
        path = os.path.join(HERE, "pdfs/issue-463-example.pdf")
        with pdfplumber.open(path) as pdf:
            annots = pdf.annots
            annots[0]["contents"] == "日本語"

    def test_issue_598(self):
        """
        Ligatures should be translated by default.
        """
        path = os.path.join(HERE, "pdfs/issue-598-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            a = page.extract_text()
            assert "fiction" in a
            assert "ﬁction" not in a

            b = page.extract_text(expand_ligatures=False)
            assert "ﬁction" in b
            assert "fiction" not in b

            assert page.extract_words()[53]["text"] == "fiction"
            assert page.extract_words(expand_ligatures=False)[53]["text"] == "ﬁction"

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

    def test_issue_982(self):
        """
        extract_text(use_text_flow=True) apparently does nothing

        This is because, while we took care not to sort the words by
        `doctop` in `WordExtractor` and `WordMap`, no such precaution
        was taken in `cluster_objects`.  We thus add an option to
        `cluster_objects` to preserve the ordering (which could come
        from `use_text_flow` or from `presorted`) of the input objects.
        """
        path = os.path.join(HERE, "pdfs/issue-982-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            text = re.sub(r"\s+", " ", page.extract_text(use_text_flow=True))
            words = " ".join(w["text"] for w in page.extract_words(use_text_flow=True))
            assert text[0:100] == words[0:100]

    def test_issue_1089(self):
        """
        Page.to_image() leaks file descriptors

        This is because PyPdfium2 leaks file descriptors.  Explicitly
        close the `PdfDocument` to prevent this.
        """
        # Skip test on platforms without getrlimit
        if resource is None:
            return
        # Any PDF will do
        path = os.path.join(HERE, "pdfs/test-punkt.pdf")
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        with pdfplumber.open(path) as pdf:
            for idx in range(soft):
                _ = pdf.pages[0].to_image()
        # We're still alive
        assert True

    def test_issue_1147(self):
        """
        Edge-case for when decode_text is passed a string
        that is out of bounds of PDFDocEncoding
        """
        path = os.path.join(HERE, "pdfs/issue-1147-example.pdf")
        with pdfplumber.open(path) as pdf:
            page = pdf.pages[0]
            # Should not error:
            assert page.extract_text()

    def test_issue_1181(self):
        """
        Correctly re-calculate coordinates when MediaBox does not start at (0,0)
        """
        path = os.path.join(HERE, "pdfs/issue-1181.pdf")
        with pdfplumber.open(path) as pdf:
            p0, p1 = pdf.pages
            assert p0.crop(p0.bbox).extract_table() == [
                ["FooCol1", "FooCol2", "FooCol3"],
                ["Foo4", "Foo5", "Foo6"],
                ["Foo7", "Foo8", "Foo9"],
                ["Foo10", "Foo11", "Foo12"],
                ["", "", ""],
            ]
            assert p1.crop(p1.bbox).extract_table() == [
                ["BarCol1", "BarCol2", "BarCol3"],
                ["Bar4", "Bar5", "Bar6"],
                ["Bar7", "Bar8", "Bar9"],
                ["Bar10", "Bar11", "Bar12"],
                ["", "", ""],
            ]
