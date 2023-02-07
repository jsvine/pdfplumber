#!/usr/bin/env python
import logging
import os
import unittest

import pdfplumber

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/issue-71-duplicate-chars.pdf")
        self.pdf = pdfplumber.open(path)

    @classmethod
    def teardown_class(self):
        self.pdf.close()

    def test_extract_table(self):
        page = self.pdf.pages[0]
        table_without_drop_duplicates = page.extract_table()
        table_with_drop_duplicates = page.dedupe_chars().extract_table()
        last_line_without_drop = table_without_drop_duplicates[1][1].split("\n")[-1]
        last_line_with_drop = table_with_drop_duplicates[1][1].split("\n")[-1]

        assert last_line_without_drop == "微微软软 培培训训课课程程：： 名名模模意意义义一一些些有有意意义义一一些些"
        assert last_line_with_drop == "微软 培训课程： 名模意义一些有意义一些"

    def test_extract_words(self):
        page = self.pdf.pages[0]
        x0 = 440.143
        x1_without_drop = 534.992
        x1_with_drop = 534.719
        top_windows = 791.849
        top_linux = 794.357
        bottom = 802.961
        last_words_without_drop = page.extract_words()[-1]
        last_words_with_drop = page.dedupe_chars().extract_words()[-1]

        assert round(last_words_without_drop["x0"], 3) == x0
        assert round(last_words_without_drop["x1"], 3) == x1_without_drop
        assert round(last_words_without_drop["top"], 3) in (top_windows, top_linux)
        assert round(last_words_without_drop["bottom"], 3) == bottom
        assert last_words_without_drop["upright"] == 1
        assert last_words_without_drop["text"] == "名名模模意意义义一一些些有有意意义义一一些些"

        assert round(last_words_with_drop["x0"], 3) == x0
        assert round(last_words_with_drop["x1"], 3) == x1_with_drop
        assert round(last_words_with_drop["top"], 3) in (top_windows, top_linux)
        assert round(last_words_with_drop["bottom"], 3) == bottom
        assert last_words_with_drop["upright"] == 1
        assert last_words_with_drop["text"] == "名模意义一些有意义一些"

    def test_extract_text(self):
        page = self.pdf.pages[0]
        last_line_without_drop = page.extract_text().split("\n")[-1]
        last_line_with_drop = page.dedupe_chars().extract_text().split("\n")[-1]

        assert last_line_without_drop == "微微软软 培培训训课课程程：： 名名模模意意义义一一些些有有意意义义一一些些"
        assert last_line_with_drop == "微软 培训课程： 名模意义一些有意义一些"

    def test_extract_text2(self):
        path = os.path.join(HERE, "pdfs/issue-71-duplicate-chars-2.pdf")
        pdf = pdfplumber.open(path)
        page = pdf.pages[0]

        assert (
            page.dedupe_chars().extract_text(y_tolerance=6).splitlines()[4]
            == "UE 8. Circulation - Métabolismes"
        )
