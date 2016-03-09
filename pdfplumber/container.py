from itertools import chain
from pdfplumber import utils

def rect_to_edges(rect):
    top, bottom, left, right = [ dict(rect) for x in range(4) ]
    top.update({
        "object_type": "rect_edge",
        "height": 0,
        "y0": rect["y1"],
        "orientation": "h"
    })
    bottom.update({
        "object_type": "rect_edge",
        "height": 0,
        "doctop": rect["doctop"] + rect["height"],
        "y1": rect["y0"],
        "orientation": "h"
    })
    left.update({
        "object_type": "rect_edge",
        "width": 0,
        "x1": rect["x0"],
        "orientation": "v"
    })
    right.update({
        "object_type": "rect_edge",
        "width": 0,
        "x0": rect["x1"],
        "orientation": "v"
    })
    return [ top, bottom, left, right ]

def line_to_edge(line):
    edge = dict(line)
    edge["orientation"] = "h" if (line["y0"] == line["y1"]) else "v"
    return edge

class Container(object):
    cached_properties = [ "_rect_edges", "_edges", "_objects" ]

    def flush_cache(self, properties=None):
        props = self.cached_properties if properties == None else properties
        for p in props:
            if hasattr(self, p):
                delattr(self, p)

    @property
    def rects(self):
        return self.objects.get("rect", [])

    @property
    def lines(self):
        return self.objects.get("line", [])

    @property
    def images(self):
        return self.objects.get("image", [])

    @property
    def figures(self):
        return self.objects.get("figure", [])

    @property
    def chars(self):
        return self.objects.get("char", [])

    @property
    def annos(self):
        return self.objects.get("anno", [])

    @property
    def rect_edges(self):
        if hasattr(self, "_rect_edges"): return self._edges
        rect_edges_gen = (rect_to_edges(r) for r in self.rects)
        self._rect_edges = list(chain(*rect_edges_gen))
        return self._rect_edges

    @property
    def edges(self):
        if hasattr(self, "_edges"): return self._edges
        line_edges = list(map(line_to_edge, self.lines))
        self._edges = self.rect_edges + line_edges
        return self._edges
