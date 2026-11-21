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

        assert (
            last_line_without_drop
            == "微微软软 培培训训课课程程：： 名名模模意意义义一一些些有有意意义义一一些些"
        )
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
        assert (
            last_words_without_drop["text"]
            == "名名模模意意义义一一些些有有意意义义一一些些"
        )

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

        assert (
            last_line_without_drop
            == "微微软软 培培训训课课程程：： 名名模模意意义义一一些些有有意意义义一一些些"
        )
        assert last_line_with_drop == "微软 培训课程： 名模意义一些有意义一些"

    def test_extract_text2(self):
        path = os.path.join(HERE, "pdfs/issue-71-duplicate-chars-2.pdf")
        pdf = pdfplumber.open(path)
        page = pdf.pages[0]

        assert (
            page.dedupe_chars().extract_text(y_tolerance=6).splitlines()[4]
            == "UE 8. Circulation - Métabolismes"
        )

    def test_extra_attrs(self):
        path = os.path.join(HERE, "pdfs/issue-1114-dedupe-chars.pdf")
        pdf = pdfplumber.open(path)
        page = pdf.pages[0]

        def dup_chars(s: str) -> str:
            return "".join((char if char == " " else char + char) for char in s)

        ground_truth = (
            ("Simple", False, False),
            ("Duplicated", True, True),
            ("Font", "fontname", True),
            ("Size", "size", True),
            ("Italic", "fontname", True),
            ("Weight", "fontname", True),
            ("Horizontal shift", False, "HHoorrizizoonntatal ls shhifitft"),
            ("Vertical shift", False, True),
        )
        gt = []
        for text, should_dedup, dup_text in ground_truth:
            if isinstance(dup_text, bool):
                if dup_text:
                    dup_text = dup_chars(text)
                else:
                    dup_text = text
            gt.append((text, should_dedup, dup_text))

        keys_list = ["no_dedupe", (), ("size",), ("fontname",), ("size", "fontname")]
        for keys in keys_list:
            if keys != "no_dedupe":
                filtered_page = page.dedupe_chars(tolerance=2, extra_attrs=keys)
            else:
                filtered_page = page
            for i, line in enumerate(
                filtered_page.extract_text(y_tolerance=5).splitlines()
            ):
                text, should_dedup, dup_text = gt[i]
                if keys == "no_dedupe":
                    should_dedup = False
                if isinstance(should_dedup, str):
                    if should_dedup in keys:
                        fail_msg = (
                            f"{should_dedup} is not required to match "
                            "so it should be duplicated"
                        )
                        assert line == dup_text, fail_msg
                    else:
                        fail_msg = (
                            "Should not be duplicated "
                            f"when requiring matching {should_dedup}"
                        )
                        assert line == text, fail_msg
                elif should_dedup:
                    assert line == text
                else:
                    assert line == dup_text

    def test_order_follows_the_first_occurrence(self):
        a = {"upright": True, "text": "a", "fontname": "F", "size": 10}
        a.update({"doctop": 0, "x0": 0})
        b = dict(a, text="b", x0=10)
        assert pdfplumber.utils.dedupe_chars([a, b, a]) == [a, b]
        assert pdfplumber.utils.dedupe_chars([b, a, dict(a, x0=0.2)]) == [b, a]

    def test_order_is_restored_without_scanning_the_list(self):
        # `chars.index` scans the list once per kept char: quadratic on a page
        class Unscannable(list):
            def index(self, *args, **kwargs):
                raise AssertionError("dedupe_chars scanned the list")

        a = {"upright": True, "text": "a", "fontname": "F", "size": 10}
        a.update({"doctop": 0, "x0": 0})
        chars = Unscannable([a, dict(a, x0=0.2), dict(a, text="b", x0=10)])
        assert pdfplumber.utils.dedupe_chars(chars) == [chars[0], chars[2]]
