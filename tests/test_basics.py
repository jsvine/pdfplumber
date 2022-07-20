#!/usr/bin/env python
import logging
import os
import unittest

import pytest

import pdfplumber

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        self.pdf = pdfplumber.open(path)

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_metadata(self):
        metadata = self.pdf.metadata
        assert isinstance(metadata["Producer"], str)

    def test_pagecount(self):
        assert len(self.pdf.pages) == 1

    def test_page_number(self):
        assert self.pdf.pages[0].page_number == 1
        assert str(self.pdf.pages[0]) == "<Page:1>"

    def test_objects(self):
        assert len(self.pdf.chars)
        assert len(self.pdf.rects)
        assert len(self.pdf.lines)
        assert len(self.pdf.rect_edges)
        # Ensure that caching is working:
        assert id(self.pdf._rect_edges) == id(self.pdf.rect_edges)
        assert id(self.pdf.pages[0]._layout) == id(self.pdf.pages[0].layout)

    def test_annots(self):
        # via http://www.pdfill.com/example/pdf_drawing_new.pdf
        path = os.path.join(HERE, "pdfs/pdffill-demo.pdf")
        with pdfplumber.open(path) as pdf:
            assert len(pdf.annots)
            assert len(pdf.hyperlinks) == 17
            uri = "http://www.pdfill.com/pdf_drawing.html"
            assert pdf.hyperlinks[0]["uri"] == uri

        path = os.path.join(HERE, "pdfs/annotations.pdf")
        with pdfplumber.open(path) as pdf:
            assert len(pdf.annots)

    def test_crop_and_filter(self):
        def test(obj):
            return obj["object_type"] == "char"

        bbox = (0, 0, 200, 200)
        original = self.pdf.pages[0]
        cropped = original.crop(bbox)
        assert id(cropped.chars) == id(cropped._objects["char"])
        assert cropped.width == 200
        assert len(cropped.rects) > 0
        assert len(cropped.chars) < len(original.chars)

        within_bbox = original.within_bbox(bbox)
        assert len(within_bbox.chars) < len(cropped.chars)
        assert len(within_bbox.chars) > 0

        filtered = cropped.filter(test)
        assert id(filtered.chars) == id(filtered._objects["char"])
        assert len(filtered.rects) == 0

    def test_outside_bbox(self):
        original = self.pdf.pages[0]
        outside_bbox = original.outside_bbox(original.find_tables()[0].bbox)
        assert outside_bbox.extract_text() == "Page 1 of 205"
        assert outside_bbox.bbox == original.bbox

    def test_relative_crop(self):
        page = self.pdf.pages[0]
        cropped = page.crop((10, 10, 40, 40))
        recropped = cropped.crop((10, 15, 20, 25), relative=True)
        target_bbox = (20, 25, 30, 35)
        assert recropped.bbox == target_bbox

        recropped_wi = cropped.within_bbox((10, 15, 20, 25), relative=True)
        assert recropped_wi.bbox == target_bbox

        # via issue #245, should not throw error when using `relative=True`
        bottom = page.crop((0, 0.8 * float(page.height), page.width, page.height))
        bottom.crop((0, 0, 0.5 * float(bottom.width), bottom.height), relative=True)
        bottom.crop(
            (0.5 * float(bottom.width), 0, bottom.width, bottom.height), relative=True
        )

    def test_invalid_crops(self):
        page = self.pdf.pages[0]
        with pytest.raises(ValueError):
            page.crop((0, 0, 0, 0))

        with pytest.raises(ValueError):
            page.crop((0, 0, 10000, 10))

        with pytest.raises(ValueError):
            page.crop((-10, 0, 10, 10))

        with pytest.raises(ValueError):
            page.crop((100, 0, 0, 100))

        with pytest.raises(ValueError):
            page.crop((0, 100, 100, 0))

        # via issue #245
        bottom = page.crop((0, 0.8 * float(page.height), page.width, page.height))
        with pytest.raises(ValueError):
            bottom.crop((0, 0, 0.5 * float(bottom.width), bottom.height))
        with pytest.raises(ValueError):
            bottom.crop((0.5 * float(bottom.width), 0, bottom.width, bottom.height))

        # via issue #421, testing strict=True/False
        with pytest.raises(ValueError):
            page.crop((0, 0, page.width + 10, page.height + 10))

        page.crop((0, 0, page.width + 10, page.height + 10), strict=False)

    def test_rotation(self):
        assert self.pdf.pages[0].width == 1008
        assert self.pdf.pages[0].height == 612
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11-rotated.pdf")
        with pdfplumber.open(path) as rotated:
            assert rotated.pages[0].width == 612
            assert rotated.pages[0].height == 1008

            assert rotated.pages[0].cropbox == self.pdf.pages[0].cropbox
            assert rotated.pages[0].bbox != self.pdf.pages[0].bbox

    def test_password(self):
        path = os.path.join(HERE, "pdfs/password-example.pdf")
        with pdfplumber.open(path, password="test") as pdf:
            assert len(pdf.chars) > 0

    def test_colors(self):
        rect = self.pdf.pages[0].rects[0]
        assert rect["non_stroking_color"] == [0.8, 1, 1]

    def test_text_colors(self):
        char = self.pdf.pages[0].chars[3358]
        assert char["non_stroking_color"] == [1, 0, 0]

    def test_load_with_custom_laparams(self):
        # See https://github.com/jsvine/pdfplumber/issues/168
        path = os.path.join(HERE, "pdfs/cupertino_usd_4-6-16.pdf")
        laparams = dict(line_margin=0.2)
        with pdfplumber.open(path, laparams=laparams) as pdf:
            assert round(pdf.pages[0].chars[0]["top"], 3) == 66.384

    def test_loading_pathobj(self):
        from pathlib import Path

        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        path_obj = Path(path)
        with pdfplumber.open(path_obj) as pdf:
            assert len(pdf.metadata)

    def test_loading_fileobj(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        with open(path, "rb") as f:
            with pdfplumber.open(f) as pdf:
                assert len(pdf.metadata)
            assert not f.closed

    def test_bad_fileobj(self):
        path = os.path.join(HERE, "pdfs/empty.pdf")
        with pytest.raises(pdfplumber.pdf.PSException):
            pdfplumber.open(path)

        f = open(path)
        with pytest.raises(pdfplumber.pdf.PSException):
            pdfplumber.open(f)
        # File objects passed to pdfplumber should not be auto-closed
        assert not f.closed
        f.close()
