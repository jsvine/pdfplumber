from operator import itemgetter
import itertools
from . import utils
from . import edge_finders

def move_to_avg(objs, orientation):
    """
    Move `objs` vertically/horizontally to their average x/y position.
    """
    if orientation not in ("h", "v"):
        raise ValueError("Orientation must be 'v' or 'h'")
    if len(objs) == 0: return []
    move_axis = "v" if orientation == "h" else "h"
    attr = "top" if orientation == "h" else "x0"
    values = list(map(itemgetter(attr), objs))
    q = pow(10, utils.decimalize(values[0]).as_tuple().exponent)
    avg = utils.decimalize(float(sum(values) / len(values)), q)
    new_objs = [ utils.move_object(obj, move_axis, avg - obj[attr])
        for obj in objs ]
    return new_objs

  
DEFAULT_SNAP_TOLERANCE = 3
def snap_edges(edges, x_tolerance=DEFAULT_SNAP_TOLERANCE, y_tolerance=DEFAULT_SNAP_TOLERANCEE):

    """
    Given a list of edges, snap any within `tolerance` pixels of one another to their positional average.
    """
    v, h = [ list(filter(lambda x: x["orientation"] == o, edges))
        for o in ("v", "h") ]

    v = [ move_to_avg(cluster, "v")
        for cluster in utils.cluster_objects(v, "x0", y_tolerance) ]

    h = [ move_to_avg(cluster, "h")
        for cluster in utils.cluster_objects(h, "top", x_tolerance) ]

    snapped = list(itertools.chain(*(v + h)))
    return snapped

DEFAULT_JOIN_TOLERANCE = 3
def join_edge_group(edges, orientation, tolerance=DEFAULT_JOIN_TOLERANCE):
    """
    Given a list of edges along the same infinite line, join those that are within `tolerance` pixels of one another.
    """
    if orientation == "h":
        min_prop, max_prop = "x0", "x1"
    elif orientation == "v":
        min_prop, max_prop = "top", "bottom"
    else:
        raise ValueError("Orientation must be 'v' or 'h'")

    sorted_edges = list(sorted(edges, key=itemgetter(min_prop)))
    joined = [ sorted_edges[0] ]
    for e in sorted_edges[1:]:
        last = joined[-1]
        if e[min_prop] <= (last[max_prop] + tolerance):
            if e[max_prop] > last[max_prop]:
                # Extend current edge to new extremity
                extended = utils.bbox_to_object(
                    utils.objects_to_bbox([ last, e ])
                )
                extended["orientation"] = orientation
                joined[-1] = extended
            else:
                # Do nothing; edge is fully contained in pre-existing edge
                pass
        else:
            # Edge is separate from previous edges
            joined.append(e)

    return joined

def merge_edges(edges, snap_x_tolerance, snap_y_tolerance, join_tolerance):
    """
    Using the `snap_edges` and `join_edge_group` methods above, merge a list of edges into a more "seamless" list.
    """
    def get_group(edge):
        if edge["orientation"] == "h":
            return ("h", edge["top"])
        else:
            return ("v", edge["x0"])

    if snap_x_tolerance > 0 or snap_y_tolerance > 0:
        edges = snap_edges(edges, snap_x_tolerance, snap_y_tolerance)

    if join_tolerance > 0:
        _sorted = sorted(edges, key=get_group)
        edge_groups = itertools.groupby(_sorted, key=get_group)
        edge_gen = (join_edge_group(items, k[0], join_tolerance)
            for k, items in edge_groups)
        edges = list(itertools.chain(*edge_gen))
    return edges


def edges_to_intersections(edges, x_tolerance=1, y_tolerance=1):
    """
    Given a list of edges, return the points at which they intersect within `tolerance` pixels.
    """
    intersections = {}
    v_edges, h_edges = [ list(filter(lambda x: x["orientation"] == o, edges))
        for o in ("v", "h") ]
    for v in sorted(v_edges, key=itemgetter("x0", "top")):
        for h in sorted(h_edges, key=itemgetter("top", "x0")):
            if ((v["top"] <= (h["top"] + y_tolerance)) and
                (v["bottom"] >= (h["top"] - y_tolerance)) and
                (v["x0"] >= (h["x0"] - x_tolerance)) and
                (v["x0"] <= (h["x1"] + x_tolerance))):
                vertex = (v["x0"], h["top"])
                if vertex not in intersections:
                    intersections[vertex] = { "v": [], "h": [] }
                intersections[vertex]["v"].append(v)
                intersections[vertex]["h"].append(h)
    return intersections
    

def intersections_to_cells(intersections):
    """
    Given a list of points (`intersections`), return all retangular "cells" those points describe.

    `intersections` should be a dictionary with (x0, top) tuples as keys,
    and a list of edge objects as values. The edge objects should correspond
    to the edges that touch the intersection.
    """

    def edge_connects(p1, p2):
        def edges_to_set(edges):
            return set(map(utils.object_to_bbox, edges))

        if p1[0] == p2[0]:
            common = edges_to_set(intersections[p1]["v"])\
                .intersection(edges_to_set(intersections[p2]["v"]))
            if len(common): return True

        if p1[1] == p2[1]:
            common = edges_to_set(intersections[p1]["h"])\
                .intersection(edges_to_set(intersections[p2]["h"]))
            if len(common): return True
        return False
    
    points = list(sorted(intersections.keys()))     
    n_points = len(points)
    def find_smallest_cell(points, i):
        if i == n_points - 1: return None
        pt = points[i]
        rest = points[i+1:]
        # Get all the points directly below and directly right
        below = [ x for x in rest if x[0] == pt[0] ] 
        right = [ x for x in rest if x[1] == pt[1] ] 
        for below_pt in below:
            if not edge_connects(pt, below_pt): continue
                
            for right_pt in right:
                if not edge_connects(pt, right_pt): continue
                
                bottom_right = (right_pt[0], below_pt[1])
                
                if ((bottom_right in intersections) and
                    edge_connects(bottom_right, right_pt) and
                    edge_connects(bottom_right, below_pt)):
                    
                    return (
                        pt[0],
                        pt[1],
                        bottom_right[0],
                        bottom_right[1]
                    )

    cell_gen = (find_smallest_cell(points, i) for i in range(len(points)))
    return list(filter(None, cell_gen))

def cells_to_tables(cells):
    """
    Given a list of bounding boxes (`cells`), return a list of tables that hold those those cells most simply (and contiguously).
    """
    def bbox_to_corners(bbox):
        x0, top, x1, bottom = bbox
        return list(itertools.product((x0, x1), (top, bottom)))
    
    cells = [ {
        "available": True,
        "bbox": bbox,
        "corners": bbox_to_corners(bbox)
    } for bbox in cells ]
    
        # Iterate through the cells found above, and assign them
    # to contiguous tables
    
    def init_new_table():
        return { "corners": set([]), "cells": [] }
    
    def assign_cell(cell, table):
        table["corners"] = table["corners"].union(set(cell["corners"]))
        table["cells"].append(cell["bbox"])
        cell["available"] = False

    n_cells = len(cells)
    n_assigned = 0
    tables = []
    current_table = init_new_table()
    while True:
        initial_cell_count = len(current_table["cells"])
        for i, cell in enumerate(filter(itemgetter("available"), cells)):
            if len(current_table["cells"]) == 0:
                assign_cell(cell, current_table)
                n_assigned += 1
            else:
                corner_count = sum(c in current_table["corners"]
                    for c in cell["corners"])
                if corner_count > 0 and cell["available"]:
                    assign_cell(cell, current_table)
                    n_assigned += 1
        if n_assigned == n_cells:
            break
        if len(current_table["cells"]) == initial_cell_count:
            tables.append(current_table)
            current_table = init_new_table()

    if len(current_table["cells"]):
        tables.append(current_table)
        
    _sorted = sorted(tables, key=lambda t: min(t["corners"]))
    filtered = [ t["cells"] for t in _sorted if len(t["cells"]) > 1 ]
    return filtered

class CellGroup(object):
    def __init__(self, cells):
        self.cells = cells
        self.bbox = (
            min(map(itemgetter(0), filter(None, cells))),
            min(map(itemgetter(1), filter(None, cells))),
            max(map(itemgetter(2), filter(None, cells))),
            max(map(itemgetter(3), filter(None, cells))),
        )

class Row(CellGroup):
    pass

class Table(object):
    def __init__(self, page, cells, text_kwargs={}):
        self.page = page
        self.cells = cells
        self.bbox = (
            min(map(itemgetter(0), cells)),
            min(map(itemgetter(1), cells)),
            max(map(itemgetter(2), cells)),
            max(map(itemgetter(3), cells)),
        )
        self.text_kwargs = text_kwargs

    @property
    def rows(self):
        _sorted = sorted(self.cells, key=itemgetter(1, 0)) 
        xs = list(sorted(set(map(itemgetter(0), self.cells))))
        rows = []
        for y, row_cells in itertools.groupby(_sorted, itemgetter(1)):
            xdict = dict((cell[0], cell) for cell in row_cells)
            row = Row([ xdict.get(x) for x in xs ])
            rows.append(row)
        return rows

    def extract(self):

        chars = self.page.chars
        table_arr = []
        def char_in_bbox(char, bbox):
            v_mid = (char["top"] + char["bottom"]) / 2
            h_mid = (char["x0"] + char["x1"]) / 2
            x0, top, x1, bottom = bbox
            return (
                (h_mid >= x0) and
                (h_mid < x1) and
                (v_mid >= top) and
                (v_mid < bottom)
            )

        for row in self.rows:
            arr = []
            row_chars = [ char for char in chars
                if char_in_bbox(char, row.bbox) ]

            for cell in row.cells:
                if cell == None:
                    cell_text = None
                else:
                    cell_chars = [ char for char in row_chars
                        if char_in_bbox(char, cell) ]

                    if len(cell_chars):
                        cell_text = utils.extract_text(
                            cell_chars,
                            **self.text_kwargs
                        ).strip()
                    else:
                        cell_text = ""
                arr.append(cell_text)
            table_arr.append(arr)

        return table_arr


def v_edge_desc_to_edge(desc, page):
    if isinstance(desc, dict):
        edge = {
            "x0": desc.get("x0", desc.get("x")),
            "x1": desc.get("x1", desc.get("x")),
            "top": desc.get("top", page.bbox[1]),
            "bottom": desc.get("bottom", page.bbox[3]),
        }
    else:
        edge = {
            "x0": desc,
            "x1": desc,
            "top": page.bbox[1],
            "bottom": page.bbox[3],
        }
    edge["height"] = edge["bottom"] - edge["top"]
    edge["orientation"] = "v"
    return edge

def h_edge_desc_to_edge(desc, page):
    if isinstance(desc, dict):
        edge = {
            "x0": desc.get("x0", page.bbox[0]),
            "x1": desc.get("x1", page.bbox[2]),
            "top": desc.get("top", desc.get("bottom")),
            "bottom": desc.get("bottom", desc.get("top")),
        }
    else:
        edge = {
            "x0": page.bbox[0],
            "x1": page.bbox[2],
            "top": desc,
            "bottom": desc,
        }
    edge["width"] = edge["x1"] - edge["x0"]
    edge["orientation"] = "h"
    return edge

DEFAULT_TABLE_SETTINGS = {
    "vertical_edges": None,
    "horizontal_edges": None,
    "snap_tolerance": DEFAULT_SNAP_TOLERANCE,
    "snap_x_tolerance": None,
    "snap_y_tolerance": None,
    "join_tolerance": DEFAULT_JOIN_TOLERANCE,
    "intersection_tolerance": 3,
    "intersection_x_tolerance": None,
    "intersection_y_tolerance": None,
    "text_kwargs": {}
}

class TableFinder(object):
    """
    Given a PDF page, find plausible table structures.

    Largely borrowed from Anssi Nurminen's master's thesis: http://dspace.cc.tut.fi/dpub/bitstream/handle/123456789/21520/Nurminen.pdf?sequence=3

    ... and inspired by Tabula: https://github.com/tabulapdf/tabula-extractor/issues/16
    """
    def __init__(self, page, settings={}):
        for k in settings.keys():
            if k not in DEFAULT_TABLE_SETTINGS:
                raise ValueError("Unrecognized table setting: '{0}'".format(
                    k
                ))
        self.page = page
        self.settings = dict(DEFAULT_TABLE_SETTINGS)
        self.settings.update(settings)
        s = self.settings

        for var, fallback in [
            ("snap_x_tolerance", "snap_tolerance"),
            ("snap_y_tolerance", "snap_tolerance"),
            ("intersection_x_tolerance", "intersection_tolerance"),
            ("intersection_y_tolerance", "intersection_tolerance"),
        ]:
            if self.settings[var] == None:
                self.settings.update({
                    var: self.settings[fallback]
                })

        s["horizontal_edges"] = [ h_edge_desc_to_edge(e, page)
            for e in s["horizontal_edges"] or page.horizontal_edges ]

        s["vertical_edges"] = [ v_edge_desc_to_edge(e, page)
            for e in s["vertical_edges"] or page.vertical_edges ]

        self.edges = self.combine_edges(
            s["horizontal_edges"] + s["vertical_edges"]
        )

        self.intersections = edges_to_intersections(
            self.edges,
            self.settings["intersection_x_tolerance"],
            self.settings["intersection_y_tolerance"],
        )

        self.cells = intersections_to_cells(
            self.intersections
        )

        self.tables = [ Table(self.page, t)
            for t in cells_to_tables(self.cells) ]

    def combine_edges(self, edges):
        s = self.settings
        if s["snap_x_tolerance"] > 0 or s["snap_y_tolerance"] > 0 or s["join_tolerance"] > 0:
            edges = merge_edges(edges,
                snap_tolerance=s["snap_x_tolerance"]
                snap_tolerance=s["snap_y_tolerance"],
                join_tolerance=s["join_tolerance"],
            )

        return edges
