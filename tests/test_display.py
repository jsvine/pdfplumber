#!/usr/bin/env python
import io
import logging
import os
import unittest
from zipfile import ZipFile

import PIL.Image
import pytest

import pdfplumber
from pdfplumber.table import TableFinder

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        self.pdf = pdfplumber.open(path)
        self.im = self.pdf.pages[0].to_image()

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_basic_conversion(self):
        self.im.reset()
        self.im.draw_rects(self.im.page.rects)
        self.im.draw_circle(self.im.page.chars[0])
        self.im.draw_line(self.im.page.edges[0])
        self.im.draw_vlines([10])
        self.im.draw_hlines([10])

    def test_width_height(self):
        p = self.pdf.pages[0]
        with pytest.raises(ValueError):
            p.to_image(resolution=72, height=100)

        im = p.to_image(width=503)
        assert im.original.width == 503

        im = p.to_image(height=805)
        assert im.original.height == 805

    def test_debug_tablefinder(self):
        self.im.reset()
        settings = {"horizontal_strategy": "text", "intersection_tolerance": 5}
        self.im.debug_tablefinder(settings)
        finder = TableFinder(self.im.page, settings)
        self.im.debug_tablefinder(finder)

        self.im.debug_tablefinder(None)

        with pytest.raises(ValueError):
            self.im.debug_tablefinder(0)

    def test_bytes_stream_to_image(self):
        path = os.path.join(HERE, "pdfs/nics-background-checks-2015-11.pdf")
        page = pdfplumber.PDF(io.BytesIO(open(path, "rb").read())).pages[0]
        page.to_image()

    def test_curves(self):
        path = os.path.join(HERE, "../examples/pdfs/ag-energy-round-up-2017-02-24.pdf")
        page = pdfplumber.open(path).pages[0]
        im = page.to_image()
        im.draw_lines(page.curves)

    def test_cropped(self):
        im = self.pdf.pages[0].crop((10, 20, 30, 50)).to_image()
        assert im.original.size == (20, 30)

    def test_copy(self):
        assert self.im.copy().original == self.im.original

    def test_outline_words(self):
        self.im.outline_words(
            stroke="blue",
            fill=(0, 200, 10),
            stroke_width=2,
            x_tolerance=5,
            y_tolerance=5,
        )

    def test_outline_chars(self):
        self.im.outline_chars(stroke="blue", fill=(0, 200, 10), stroke_width=2)

    def test__repr_png_(self):
        png = self.im._repr_png_()
        assert isinstance(png, bytes)
        assert 20000 < len(png) < 80000

    def test_no_quantize(self):
        b = io.BytesIO()
        self.im.save(b, "PNG", quantize=False)
        assert len(b.getvalue()) > len(self.im._repr_png_())

    def test_antialias(self):
        aa = self.pdf.pages[0].to_image(antialias=True)
        assert len(aa._repr_png_()) > len(self.im._repr_png_())

    def test_decompression_bomb(self):
        original_max = PIL.Image.MAX_IMAGE_PIXELS
        PIL.Image.MAX_IMAGE_PIXELS = 10
        # Previously, this raised PIL.Image.DecompressionBombError
        self.pdf.pages[0].to_image()
        PIL.Image.MAX_IMAGE_PIXELS = original_max

    def test_password(self):
        path = os.path.join(HERE, "pdfs/password-example.pdf")
        with pdfplumber.open(path, password="test") as pdf:
            pdf.pages[0].to_image()

    def test_zip(self):
        # See https://github.com/jsvine/pdfplumber/issues/948
        # reproducer.py
        path = os.path.join(HERE, "pdfs/issue-948.zip")
        with ZipFile(path) as zip_file:
            with zip_file.open("dummy.pdf") as pdf_file:
                with pdfplumber.open(pdf_file) as pdf:
                    page = pdf.pages[0]
                    page.to_image()
