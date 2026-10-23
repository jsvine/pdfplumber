#!/usr/bin/env python
import logging
import os

import pytest
from pdfminer.pdftypes import PDFObjRef
from pdfminer.psparser import PSLiteral

import pdfplumber
from pdfplumber import page as page_module
from pdfplumber.page import get_object_kind, is_resolved

logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))

PDFS = [
    "nics-background-checks-2015-11.pdf",  # chars, rects, lines
    "pdffill-demo.pdf",  # curves, images, colors
    "issue-1181.pdf",  # non-zero MediaBox origin
    "nics-background-checks-2015-11-rotated.pdf",  # rotated page
    "line-char-render-example.pdf",
    "2023-06-20-PV.pdf",
]


class TestProcessObject:
    def test_get_object_kind(self):
        assert get_object_kind("LTChar") == "char"
        assert get_object_kind("LTCurve") == "curve"
        assert get_object_kind("LTTextBoxHorizontal") == "textboxhorizontal"

    def test_is_resolved(self):
        assert is_resolved(1.5)
        assert is_resolved(2)
        assert is_resolved("text")
        assert is_resolved(True)
        assert is_resolved(None)
        assert is_resolved(())
        assert is_resolved((1, 0.5, 0, 0, 1, 0))
        assert is_resolved((1, "a", None))

        # Anything that might need resolving still goes through `resolve_all`
        assert not is_resolved([1, 2])
        assert not is_resolved({"a": 1})
        assert not is_resolved(b"bytes")
        assert not is_resolved(PSLiteral("name"))
        assert not is_resolved(PDFObjRef(None, 1))
        assert not is_resolved((1, [2]))
        assert not is_resolved((1, PDFObjRef(None, 1)))

        class Str(str):
            pass

        assert not is_resolved(Str("subclass"))

    @pytest.mark.parametrize("name", PDFS)
    @pytest.mark.parametrize("laparams", [None, {}])
    def test_objects_equal_resolve_all_for_every_attribute(
        self, name, laparams, monkeypatch
    ):
        """`Page.objects` must be identical whether or not scalar attributes
        skip `resolve_all`."""
        with pdfplumber.open(
            os.path.join(HERE, "pdfs", name), laparams=laparams
        ) as pdf:
            for page in pdf.pages[:3]:
                page.layout  # Parse once, so both runs see the same layout
                fast = page.parse_objects()

                monkeypatch.setattr(page_module, "is_resolved", lambda v: False)
                slow = page.parse_objects()
                monkeypatch.undo()

                assert fast == slow
                for kind in fast:
                    for a, b in zip(fast[kind], slow[kind]):
                        assert list(a.keys()) == list(b.keys())
                        assert [type(v) for v in a.values()] == [
                            type(v) for v in b.values()
                        ]
