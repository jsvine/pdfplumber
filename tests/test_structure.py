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
WORDS = {
    0: ["Titre", "du", "document"],
    1: ["Titre", "1"],
    2: ["Contenu", "1,", "contenu", "2,", "contenu", "3."],
    3: [
        "Lorem",
        "ipsum",
        "dolor",
        "sit",
        "amet,",
        "consectetur",
        "adipiscing",
        "elit,",
        "sed",
        "do",
        "eiusmod",
        "tempor",
        "incididunt",
        "ut",
        "labore",
        "et",
    ],
    4: [
        "dolore",
        "magna",
        "aliqua.",
        "Ut",
        "enim",
        "ad",
        "minim",
        "veniam,",
        "quis",
        "nostrud",
        "exercitation",
        "ullamco",
        "laboris",
        "nisi",
        "ut",
    ],
    5: [
        "aliquip",
        "ex",
        "ea",
        "commodo",
        "consequat.",
        "Duis",
        "aute",
        "irure",
        "dolor",
        "in",
        "reprehenderit",
        "in",
        "voluptate",
        "velit",
        "esse",
        "cillum",
    ],
    6: [
        "dolore",
        "eu",
        "fugiat",
        "nulla",
        "pariatur.",
        "Excepteur",
        "sint",
        "occaecat",
        "cupidatat",
        "non",
        "proident,",
        "sunt",
        "in",
        "culpa",
        "qui",
        "officia",
    ],
    7: ["deserunt", "mollit", "anim", "id", "est", "laborum."],
    8: ["Titre", "2"],
    9: ["Encore", "du", "contenu!"],
    10: ["1."],
    11: ["Énumération", "1"],
    12: ["2."],
    13: ["Énumération", "2"],
    14: ["a)"],
    15: ["Énumération", "imbriquée"],
    16: ["3."],
    17: ["Longue", "énumération"],
    19: [
        ":",
        "Lorem",
        "ipsum",
        "dolor",
        "sit",
        "amet,",
        "consectetur",
        "adipiscing",
        "elit,",
        "sed",
        "do",
        "eiusmod",
    ],
    20: [
        "tempor",
        "incididunt",
        "ut",
        "labore",
        "et",
        "dolore",
        "magna",
        "aliqua.",
        "Ut",
        "enim",
        "ad",
        "minim",
        "veniam,",
        "quis",
        "nostrud",
    ],
    21: [
        "exercitation",
        "ullamco",
        "laboris",
        "nisi",
        "ut",
        "aliquip",
        "ex",
        "ea",
        "commodo",
        "consequat.",
        "Duis",
        "aute",
        "irure",
        "dolor",
        "in",
    ],
    22: [
        "reprehenderit",
        "in",
        "voluptate",
        "velit",
        "esse",
        "cillum",
        "dolore",
        "eu",
        "fugiat",
        "nulla",
        "pariatur.",
        "Excepteur",
        "sint",
    ],
    23: [
        "occaecat",
        "cupidatat",
        "non",
        "proident,",
        "sunt",
        "in",
        "culpa",
        "qui",
        "officia",
        "deserunt",
        "mollit",
        "anim",
        "id",
        "est",
        "laborum.",
    ],
    24: ["Tableau"],
    25: ["Chose"],
    26: ["Truc"],
    27: ["Chose", "1"],
    28: ["Truc", "1"],
    29: ["Chose", "2"],
    30: ["Truc", "2"],
}


class Test(unittest.TestCase):
    """Test a PDF specifically created to show structure."""

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

    def test_mcids_chars(self):
        marked_chars = defaultdict(str)
        for c in self.pdf.pages[0].chars:
            if c.get("mcid") is not None:
                marked_chars[c["mcid"]] += c["text"]
        assert marked_chars == TEXT

    def test_mcids_words(self):
        marked_words = defaultdict(list)
        for w in self.pdf.pages[0].extract_words(extra_attrs=["mcid"]):
            if w.get("mcid") is not None:
                marked_words[w["mcid"]].append(w["text"])
        assert marked_words == WORDS


SCOTUS = {
    1: [
        "IN",
        "THE",
        "SUPREME",
        "COURT",
        "OF",
        "THE",
        "UNITED",
        "STATES",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "x",
        "MICHAEL",
        "A.",
        "KNOWLES,",
        ":",
        "WARDEN,",
        ":",
    ],
    2: ["Petitioner", ":"],
    3: ["v."],
    4: [
        ":",
        "No.",
        "07-1315",
        "ALEXANDRE",
        "MIRZAYANCE.",
        ":",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "x",
    ],
    5: ["Washington,", "D.C.", "Tuesday,", "January", "13,", "2009"],
    6: [
        "The",
        "above-entitled",
        "matter",
        "came",
        "on",
        "for",
        "oral",
        "argument",
        "before",
        "the",
        "Supreme",
        "Court",
        "of",
        "the",
        "United",
        "States",
        "at",
        "1:01",
        "p.m.",
        "APPEARANCES:",
        "STEVEN",
        "E.",
        "MERCER,",
        "ESQ.,",
        "Deputy",
        "Attorney",
        "General,",
        "Los",
    ],
    7: [
        "Angeles,",
        "Cal.;",
        "on",
        "behalf",
        "of",
        "the",
        "Petitioner.",
        "CHARLES",
        "M.",
        "SEVILLA,",
        "ESQ.,",
        "San",
        "Diego,",
        "Cal.;",
        "on",
        "behalf",
        "of",
        "the",
        "Respondent.",
    ],
    8: ["1"],
    9: ["Alderson", "Reporting", "Company"],
}


PVSTRUCT1 = [
    {
        "type": "Sect",
        "children": [
            {"lang": "FR-CA", "type": "P", "mcids": [0]},
            {"lang": "FR-CA", "type": "P", "mcids": [1]},
            {"lang": "FR-CA", "type": "P", "mcids": [2]},
            {"lang": "FR-CA", "type": "P", "mcids": [3]},
            {"lang": "FR-CA", "type": "P", "mcids": [4]},
            {"lang": "FR-CA", "type": "P", "mcids": [5]},
            {"lang": "FR-CA", "type": "P", "mcids": [6]},
            {
                "type": "L",
                "children": [
                    {
                        "type": "LI",
                        "children": [
                            {
                                "lang": "FR-CA",
                                "type": "LBody",
                                "mcids": [9, 11],
                                "children": [
                                    {"lang": "FR-FR", "type": "Span", "mcids": [10]}
                                ],
                            }
                        ],
                    }
                ],
            },
            {"lang": "FR-CA", "type": "P", "mcids": [14]},
            {"lang": "FR-CA", "type": "P", "mcids": [15]},
            {"lang": "FR-CA", "type": "P", "mcids": [16]},
            {"lang": "FR-FR", "type": "P", "mcids": [17]},
            {"lang": "FR-FR", "type": "P", "mcids": [18]},
            {"lang": "FR-FR", "type": "P", "mcids": [19]},
        ],
    }
]


class TestMany(unittest.TestCase):
    """Test various PDFs."""

    def test_scotus(self):
        path = os.path.join(HERE, "pdfs/scotus-transcript-p1.pdf")
        pdf = pdfplumber.open(path)
        marked_words = defaultdict(list)
        page = pdf.pages[0]
        for w in page.extract_words(extra_attrs=["mcid"]):
            if w.get("mcid") is not None:
                marked_words[w["mcid"]].append(w["text"])
        assert marked_words == SCOTUS

    def test_proces_verbal(self):
        path = os.path.join(HERE, "pdfs/2023-06-20-PV.pdf")

        pdf = pdfplumber.open(path)
        page = pdf.pages[1]
        assert page.structure_tree == PVSTRUCT1
