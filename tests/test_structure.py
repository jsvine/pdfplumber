#!/usr/bin/env python3

import os
import unittest
from collections import defaultdict
from io import BytesIO

import pdfplumber

HERE = os.path.abspath(os.path.dirname(__file__))
TREE = [
    {
        "type": "Document",
        "children": [
            {"type": "P", "mcids": [0]},
            {"type": "H1", "mcids": [1]},
            {"type": "P", "mcids": [2]},
            {"type": "P", "mcids": [3, 4, 5, 6, 7]},
            {"type": "H2", "mcids": [8]},
            {"type": "P", "mcids": [9]},
            {
                "type": "L",
                "children": [
                    {
                        "type": "LI",
                        "children": [
                            {
                                "type": "LBody",
                                "children": [{"type": "P", "mcids": [10, 11]}],
                            }
                        ],
                    },
                    {
                        "type": "LI",
                        "children": [
                            {
                                "type": "LBody",
                                "children": [
                                    {"type": "P", "mcids": [12, 13]},
                                    {
                                        "type": "L",
                                        "children": [
                                            {
                                                "type": "LI",
                                                "children": [
                                                    {
                                                        "type": "LBody",
                                                        "children": [
                                                            {
                                                                "type": "P",
                                                                "mcids": [14, 15],
                                                            }
                                                        ],
                                                    }
                                                ],
                                            }
                                        ],
                                    },
                                ],
                            }
                        ],
                    },
                    {
                        "type": "LI",
                        "children": [
                            {
                                "type": "LBody",
                                "children": [
                                    {
                                        "type": "P",
                                        "mcids": [16, 17, 18, 19, 20, 21, 22, 23],
                                    }
                                ],
                            }
                        ],
                    },
                ],
            },
            {"type": "H3", "mcids": [24]},
            {
                "type": "Table",
                "children": [
                    {
                        "type": "TR",
                        "children": [
                            {"type": "TH", "children": [{"type": "P", "mcids": [25]}]},
                            {"type": "TH", "children": [{"type": "P", "mcids": [26]}]},
                        ],
                    },
                    {
                        "type": "TR",
                        "children": [
                            {"type": "TD", "children": [{"type": "P", "mcids": [27]}]},
                            {"type": "TD", "children": [{"type": "P", "mcids": [28]}]},
                        ],
                    },
                    {
                        "type": "TR",
                        "children": [
                            {"type": "TD", "children": [{"type": "P", "mcids": [29]}]},
                            {"type": "TD", "children": [{"type": "P", "mcids": [30]}]},
                        ],
                    },
                ],
            },
        ],
    }
]
TEXT = {
    0: "Titre du document",
    1: "Titre 1",
    2: "Contenu 1, contenu 2, contenu 3. ",
    3: "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
    "incididunt ut labore et ",
    4: "dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation "
    "ullamco laboris nisi ut ",
    5: "aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in "
    "voluptate velit esse cillum ",
    6: "dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non "
    "proident, sunt in culpa qui officia ",
    7: "deserunt mollit anim id est laborum.",
    8: "Titre 2",
    9: "Encore du contenu!",
    10: "1.",
    11: "Énumération 1",
    12: "2.",
    13: "Énumération 2",
    14: "a)",
    15: "Énumération imbriquée",
    16: "3.",
    17: "Longue énumération",
    18: "\xa0",
    19: ": Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod ",
    20: "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, "
    "quis nostrud ",
    21: "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis "
    "aute irure dolor in ",
    22: "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. "
    "Excepteur sint ",
    23: "occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit "
    "anim id est laborum.",
    24: "Tableau",
    25: "Chose",
    26: "Truc",
    27: "Chose 1",
    28: "Truc 1",
    29: "Chose 2",
    30: "Truc 2",
}


class Test(unittest.TestCase):
    @classmethod
    def setup_class(self):
        path = os.path.join(HERE, "pdfs/pdf_structure.pdf")
        self.pdf = pdfplumber.open(path)
        with open(path, "rb") as infh:
            self.pdfbytes = BytesIO(infh.read())
        self.bytespdf = pdfplumber.open(self.pdfbytes)

    @classmethod
    def teardown_class(self):
        self.pdf.close()
        self.pdfbytes.close()
        self.bytespdf.close()

    def test_structure_tree(self):
        assert self.pdf.pages[0].structure_tree == TREE
        assert self.bytespdf.pages[0].structure_tree == TREE

    def test_mcids(self):
        marked_chars = defaultdict(str)
        for c in self.pdf.pages[0].chars:
            if "mcid" in c:
                marked_chars[c["mcid"]] += c["text"]
        assert marked_chars == TEXT
