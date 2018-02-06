#!/usr/bin/env python
import unittest
import pdfplumber
from pdfplumber import utils
import sys, os

import logging
logging.disable(logging.ERROR)

class TestUtils(unittest.TestCase):
    def test_bad_decimalize(self):
        with self.assertRaises(ValueError) as context:
            utils.decimalize("a string")

    def test_decimalize_without_q(self):
        utils.decimalize(1.2342342342, q=None)

    def test_within_bbox(self):
        bbox = (0, 0, 100, 100)
        objects = {
            "char": [
                {
                    "x0": 25,
                    "top": 25,
                    "x1": 75,
                    "bottom": 75,
                },
                {
                    "x0": 125,
                    "top": 125,
                    "x1": 175,
                    "bottom": 175,
                }
            ]    
        }
        assert utils.within_bbox(objects, bbox)["char"] == objects["char"][:1]

    def test_crop_to_bbox(self):
        bbox = (0, 0, 100, 100)
        objects = {
            "char": [
                {
                    "x0": 25,
                    "top": 25,
                    "x1": 75,
                    "bottom": 75,
                },
                {
                    "x0": 125,
                    "top": 125,
                    "x1": 175,
                    "bottom": 175,
                }
            ]    
        }
        assert utils.crop_to_bbox(objects, bbox)["char"] == objects["char"][:1]

    def test_bbox_to_object(self):
        bbox = (0, 10, 200, 210)
        rect = utils.bbox_to_object(bbox)
        assert(rect == {
            "x0": 0,
            "x1": 200,
            "top": 10,
            "bottom": 210,
            "height": 200,
            "width": 200,
        })

    def test_blank_extract_text(self):
        chars = []
        assert(utils.extract_text(chars) is None)

    def test_filter_dict(self):
        objects = { "chars": [ { "a": "b" } ], "rects": [ {} ] }
        test = lambda x: "a" in x
        f = utils.filter_objects(objects, test)
        assert(f == { "chars": [ { "a": "b" } ], "rects": [] })

    BBOXES = [
        (0, 0, 100, 100),
        (50, 50, 150, 150),
        (100, 100, 200, 200),
        (150, 150, 250, 250),
        (25, 25, 75, 75),
    ]

    def test_bboxes_overlap(self):
        r = self.BBOXES

        assert utils.bboxes_overlap(r[0], r[1])
        assert utils.bboxes_overlap_score(r[0], r[1]) == utils.IS_OVERLAPPING

        assert not utils.bboxes_overlap(r[0], r[2])
        assert utils.bboxes_overlap_score(r[0], r[2]) == utils.IS_OUTSIDE

        assert not utils.bboxes_overlap(r[0], r[3])
        assert utils.bboxes_overlap_score(r[0], r[3]) == utils.IS_OUTSIDE

        assert utils.bboxes_overlap(r[0], r[4])
        assert utils.bboxes_overlap_score(r[0], r[4]) == utils.IS_WITHIN

        assert utils.bboxes_overlap(r[4], r[0])
        assert utils.bboxes_overlap_score(r[4], r[0]) == utils.IS_OVERLAPPING

    def test_objects_overlap(self):
        r = list(map(utils.bbox_to_object, self.BBOXES))

        assert utils.objects_overlap(r[0], r[1])
        assert utils.objects_overlap_score(r[0], r[1]) == utils.IS_OVERLAPPING

        assert not utils.objects_overlap(r[0], r[2])
        assert utils.objects_overlap_score(r[0], r[2]) == utils.IS_OUTSIDE

        assert not utils.objects_overlap(r[0], r[3])
        assert utils.objects_overlap_score(r[0], r[3]) == utils.IS_OUTSIDE

        assert utils.objects_overlap(r[0], r[4])
        assert utils.objects_overlap_score(r[0], r[4]) == utils.IS_WITHIN

        assert utils.objects_overlap(r[4], r[0])
        assert utils.objects_overlap_score(r[4], r[0]) == utils.IS_OVERLAPPING

    def test_clip_object(self):
        rect = utils.bbox_to_object((0, 0, 100, 100))
        bbox = (50, 50, 75, 75)
        clipped = utils.clip_object(rect, bbox)
        assert(utils.object_to_bbox(clipped) == (50, 50, 75, 75))

    def test_cluster_objects(self):
        objects = [
            { "a": 1, "b": 2 },
            { "a": 1, "b": 4 },
            { "a": 2, "b": 1 },
        ] 

        clusters = utils.cluster_objects(objects, "a", 0)
        assert clusters[0] == objects[:2]

        clusters = utils.cluster_objects(objects, "b", 0)
        assert clusters[0] == objects[2:]

        clusters = utils.cluster_objects(objects, "b", 3)
        assert clusters[0] == objects

        fn = lambda x: x["a"] + x["b"]
        clusters = utils.cluster_objects(objects, fn, 0)
        assert clusters[0] == [ objects[0], objects[2] ]

    def test_bad_filter_edges(self):
        edges = [ {} ]
        with self.assertRaises(ValueError) as context:
            utils.filter_edges(edges, orientation="whoops")

#    def test_rects_to_edges(self):
#        rect = utils.bbox_to_object((10, 20, 30, 40))
#        rect["doctop"] = 20
#        edges = utils.rect_to_edges(rect)
#        assert edges == [
#            { "x0": 10, "top": 20, "x1": 30, "bottom": 40, "height": 20, "width": 20 },
#            { "x0": 10, "top": 20, "x1": 30, "bottom": 40, "height": 20, "width": 20 },
#            { "x0": 10, "top": 20, "x1": 30, "bottom": 40, "height": 20, "width": 20 },
#            { "x0": 10, "top": 20, "x1": 30, "bottom": 40, "height": 20, "width": 20 },
#        ]
