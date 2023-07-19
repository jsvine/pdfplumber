#!/usr/bin/env python3

import os
import unittest
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
