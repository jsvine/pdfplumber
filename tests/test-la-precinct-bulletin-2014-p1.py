#!/usr/bin/env python
import unittest
import pandas as pd
import pdfplumber
from pdfplumber.utils import within_bbox, collate_chars
import sys, os
import re

import logging
logging.disable(logging.ERROR)

HERE = os.path.abspath(os.path.dirname(__file__))

def _collate_chars(x):
    return collate_chars(x, x_tolerance=1)

def parse_results_line(chars):
    _left = chars[chars["x0rel"] < 125]
    left = _collate_chars(_left) if len(_left) else None
    _right = chars[(chars["x0rel"] > 155)]
    right = int(_collate_chars(_right)) if len(_right) else None
    _mid = chars[(chars["x0rel"] > 125) & (chars["x0rel"] < 155)]
    mid = _collate_chars(_mid) if len(_mid) else None
    return { "text": left, "aff": mid, "votes": right }

class PrecinctPage(object):
    def __init__(self, page):
        self.chars = pd.DataFrame(page.chars)
        self.lines = pd.DataFrame(page.lines)
        self.rects = pd.DataFrame(page.rects)
        self.bboxes = self.get_bboxes()
    
    def get_bboxes(self):
        outer, inner = [ r for i, r in self.rects.iterrows() ]
        col_top = inner["top"] + inner["height"]
        col_bot = outer["top"] + outer["height"]
        line_xs = self.lines["x0"].tolist()
        return {
            "h1": (outer["x0"], outer["top"], outer["x1"], inner["top"]),
            "h2": (outer["x0"], inner["top"], outer["x1"], col_top),
            "c1": (outer["x0"], col_top, line_xs[0], col_bot),
            "c2": (line_xs[0], col_top, line_xs[1], col_bot),
            "c3": (line_xs[1], col_top, line_xs[2], col_bot),
            "c4": (line_xs[2], col_top, outer["x1"], col_bot),
        }
    
    @property
    def precinct(self):
        h1_left = list(self.bboxes["h1"])
        h1_left[-2] = float(h1_left[-2]) / 2
        h1_left_chars = within_bbox(self.chars, h1_left)
        txt = h1_left_chars.groupby("top").apply(_collate_chars).iloc[-1]
        p_id = "|".join(re.split(r"\s{2,}", txt)[1:3])
        return p_id
    
    @property
    def ballots_cast(self):
        h2_chars = within_bbox(self.chars, self.bboxes["h2"])
        txt = h2_chars.groupby("top").apply(_collate_chars).iloc[0]
        return int(re.match(r"(\d+) BALLOTS CAST", txt).group(1))    
    
    @property
    def registered_voters(self):
        h2_chars = within_bbox(self.chars, self.bboxes["h2"])
        txt = h2_chars.groupby("top").apply(_collate_chars).iloc[1]
        return int(re.match(r"(\d+) REGISTERED VOTERS", txt).group(1))
    
    def parse_col(self, col_chars):
        c = col_chars.copy()
        c["x0rel"] = c["x0"] - c["x0"].min()
        results_lines = c.groupby("top").apply(parse_results_line)
        items = []
        item = {}
        vote_seen = False
        for i, r in results_lines.iteritems():
            if r["votes"] == None:
                if vote_seen == True:
                    items.append(item)
                    item = {}
                    vote_seen = False
                item["desc"] = item["desc"] + "|" + r["text"] if item.get("desc", False) else r["text"]
            if type(r["votes"]) == int:
                vote_seen = True
                item["options"] = item.get("options", [])
                item["options"].append(r)
        items.append(item)
        return items
    
    @property
    def results(self):
        r = []
        for col in [ "c1", "c2", "c3", "c4" ]:
            b = within_bbox(self.chars, self.bboxes[col])
            r += self.parse_col(b)
        return r
    
    def to_dict(self):
        return {
            "precinct": self.precinct,
            "registered_voters": self.registered_voters,
            "ballots_cast": self.ballots_cast,
            "results": self.results
        }

class Test(unittest.TestCase):

    def setUp(self):
        path = os.path.join(HERE, "pdfs/la-precinct-bulletin-2014-p1.pdf")
        self.pdf = pdfplumber.from_path(path)
        self.PDF_WIDTH = self.pdf.pages[0].width

    def test_pandas(self):
        p1 = PrecinctPage(self.pdf.pages[0]).to_dict()
        assert(p1["registered_voters"] == 1100)
        assert(p1["ballots_cast"] == 327)
        assert(p1["precinct"] == "0050003A|ACTON")
        last = p1["results"][-1]
        assert(last["desc"] == "ANTELOPE VALLEY HEALTH BD")
        assert(last["options"][-1]["text"] == "ROE LEER")
        assert(last["options"][-1]["votes"] == 39)
