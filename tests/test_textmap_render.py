import os
import re

import pytest

import pdfplumber
from pdfplumber.utils.text import TextMap, chars_to_textmap

RENDER_CASES = {
    ("ttb", "ltr"): "AB\nC\n\nDEF",
    ("ttb", "rtl"): "BA\nC\n\nFED",
    ("btt", "ltr"): "DEF\n\nC\nAB",
    ("btt", "rtl"): "FED\n\nC\nBA",
    ("ltr", "ttb"): "AC D\nB  E\n   F",
    ("ltr", "btt"): "   D\nA  E\nBC F",
    ("rtl", "ttb"): "D CA\nE  B\nF   ",
    ("rtl", "btt"): "D   \nE  A\nF CB",
}


def assert_match_chars(match, chars):
    assert match["chars"] == chars
    assert match["x0"] == min(c["x0"] for c in chars)
    assert match["x1"] == max(c["x1"] for c in chars)
    assert match["top"] == min(c["top"] for c in chars)
    assert match["bottom"] == max(c["bottom"] for c in chars)


@pytest.mark.parametrize("directions,expected", RENDER_CASES.items())
def test_rendered_textmap_search_and_lines(directions, expected):
    chars = {
        text: {"text": text, "x0": i * 10, "x1": i * 10 + 9, "top": i, "bottom": i + 8}
        for i, text in enumerate("ABCDEF")
    }
    tuples = [(text, chars.get(text)) for text in "AB\nC\n\nDEF"]
    textmap = TextMap(tuples, *directions)
    assert textmap.as_string == expected
    assert textmap.to_string() == expected
    assert textmap.to_string() == expected
    assert textmap.tuples == tuples

    matches = textmap.search(r"([A-F])", main_group=1)
    assert [m["text"] for m in matches] == re.findall(r"[A-F]", expected)
    for match in matches:
        assert match["groups"] == (match["text"],)
        assert_match_chars(match, [chars[match["text"]]])

    for strip in [False, True]:
        lines = textmap.extract_text_lines(strip=strip)
        expected_lines = [line for line in expected.split("\n") if line.strip()]
        if strip:
            expected_lines = [line.strip() for line in expected_lines]
        assert [line["text"] for line in lines] == expected_lines
        for line in lines:
            assert "groups" not in line
            assert_match_chars(line, [chars[c] for c in line["text"] if c in chars])

    assert textmap.search(r"\s+") == []
    assert textmap.search("") == []
    without_details = textmap.search("A", return_chars=False, return_groups=False)
    assert len(without_details) == 1
    assert "chars" not in without_details[0]
    assert "groups" not in without_details[0]


@pytest.mark.parametrize("directions", RENDER_CASES)
@pytest.mark.parametrize("layout", [False, True])
def test_page_search_rendered_coordinates(directions, layout):
    path = os.path.join(os.path.dirname(__file__), "pdfs/line-char-render-example.pdf")
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        line_dir, char_dir = directions
        for pattern in ["c", "f"]:
            # The "f" in this PDF is part of a ligature expanded to two letters.
            expected = page.search(pattern, regex=False)[0]
            matches = page.search(
                pattern,
                regex=False,
                layout=layout,
                line_dir_render=line_dir,
                char_dir_render=char_dir,
            )
            assert len(matches) == 1
            assert matches[0]["text"] == pattern
            assert_match_chars(matches[0], expected["chars"])


@pytest.mark.parametrize("line_dir", ["ttb", "btt"])
@pytest.mark.parametrize("char_dir", ["ltr", "rtl"])
def test_source_backed_newlines(line_dir, char_dir):
    chars = [
        {"text": text, "x0": i * 10, "x1": i * 10 + 9, "top": 0, "bottom": 10}
        for i, text in enumerate("A\nB\nC")
    ]
    textmap = TextMap([(c["text"], c) for c in chars], line_dir, char_dir)
    expected = chars[::-1] if line_dir == "btt" else chars
    assert_match_chars(textmap.search(r"(?s).+")[0], expected)


def test_source_backed_newlines_from_chars():
    chars = [
        {
            "text": text,
            "x0": i * 10,
            "x1": i * 10 + 10,
            "top": 0,
            "bottom": 10,
            "doctop": 0,
            "width": 10,
            "height": 10,
            "size": 10,
            "upright": True,
        }
        for i, text in enumerate("A\nB")
    ]
    textmap = chars_to_textmap(chars, keep_blank_chars=True, char_dir_render="rtl")
    assert textmap.as_string == "A\nB"
    assert_match_chars(textmap.search(r"(?s).+")[0], chars)


@pytest.mark.parametrize("directions", RENDER_CASES)
def test_to_string_does_not_change_cached_search(directions):
    chars = [
        {"text": text, "x0": i * 10, "x1": i * 10 + 9, "top": 0, "bottom": 10}
        for i, text in enumerate("AB\nC")
    ]
    tuples = [(c["text"], c) for c in chars]
    textmap = TextMap(tuples, *directions)
    cached_string = textmap.as_string
    assert textmap.tuples is tuples
    for new_directions in RENDER_CASES:
        textmap.line_dir_render, textmap.char_dir_render = new_directions
        expected = TextMap(tuples, *new_directions).as_string
        assert textmap.to_string() == expected
        assert textmap.to_string() == expected
        assert textmap.as_string == cached_string
        for char in [chars[0], chars[1], chars[3]]:
            assert_match_chars(textmap.search(char["text"])[0], [char])

    # Rendering retains references to source objects rather than copying them.
    chars[0]["x0"] = -10
    assert_match_chars(textmap.search("A")[0], [chars[0]])


def test_to_string_reads_current_tuples():
    char = {"text": "A", "x0": 0, "x1": 9, "top": 0, "bottom": 10}
    tuples = [("A", char)]
    textmap = TextMap(tuples, "ttb", "ltr")
    tuples.append(("B", None))
    assert textmap.tuples is tuples
    assert textmap.to_string() == "AB"
    assert textmap.to_string() == "AB"
    assert textmap.as_string == "A"
    assert_match_chars(textmap.search("A")[0], [char])
