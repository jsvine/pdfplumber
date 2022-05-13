import itertools
from dataclasses import dataclass
from operator import itemgetter
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union

from . import utils
from ._typing import T_bbox, T_num, T_obj, T_obj_iter, T_obj_list, T_point

DEFAULT_SNAP_TOLERANCE = 3
DEFAULT_JOIN_TOLERANCE = 3
DEFAULT_MIN_WORDS_VERTICAL = 3
DEFAULT_MIN_WORDS_HORIZONTAL = 1

T_intersections = Dict[T_point, Dict[str, T_obj_list]]
T_table_settings = Union["TableSettings", Dict[str, Any]]

if TYPE_CHECKING:  # pragma: nocover
    from .page import Page


def snap_edges(
    edges: T_obj_list,
    x_tolerance: T_num = DEFAULT_SNAP_TOLERANCE,
    y_tolerance: T_num = DEFAULT_SNAP_TOLERANCE,
) -> T_obj_list:
    """
    Given a list of edges, snap any within `tolerance` pixels of one another
    to their positional average.
    """
    by_orientation: Dict[str, T_obj_list] = {"v": [], "h": []}
    for e in edges:
        by_orientation[e["orientation"]].append(e)

    snapped_v = utils.snap_objects(by_orientation["v"], "x0", x_tolerance)
    snapped_h = utils.snap_objects(by_orientation["h"], "top", y_tolerance)
    return snapped_v + snapped_h


def join_edge_group(
    edges: T_obj_iter, orientation: str, tolerance: T_num = DEFAULT_JOIN_TOLERANCE
) -> T_obj_list:
    """
    Given a list of edges along the same infinite line, join those that
    are within `tolerance` pixels of one another.
    """
    if orientation == "h":
        min_prop, max_prop = "x0", "x1"
    elif orientation == "v":
        min_prop, max_prop = "top", "bottom"
    else:
        raise ValueError("Orientation must be 'v' or 'h'")

    sorted_edges = list(sorted(edges, key=itemgetter(min_prop)))
    joined = [sorted_edges[0]]
    for e in sorted_edges[1:]:
        last = joined[-1]
        if e[min_prop] <= (last[max_prop] + tolerance):
            if e[max_prop] > last[max_prop]:
                # Extend current edge to new extremity
                joined[-1] = utils.resize_object(last, max_prop, e[max_prop])
        else:
            # Edge is separate from previous edges
            joined.append(e)

    return joined


def merge_edges(
    edges: T_obj_list,
    snap_x_tolerance: T_num,
    snap_y_tolerance: T_num,
    join_x_tolerance: T_num,
    join_y_tolerance: T_num,
) -> T_obj_list:
    """
    Using the `snap_edges` and `join_edge_group` methods above,
    merge a list of edges into a more "seamless" list.
    """

    def get_group(edge: T_obj) -> Tuple[str, T_num]:
        if edge["orientation"] == "h":
            return ("h", edge["top"])
        else:
            return ("v", edge["x0"])

    if snap_x_tolerance > 0 or snap_y_tolerance > 0:
        edges = snap_edges(edges, snap_x_tolerance, snap_y_tolerance)

    _sorted = sorted(edges, key=get_group)
    edge_groups = itertools.groupby(_sorted, key=get_group)
    edge_gen = (
        join_edge_group(
            items, k[0], (join_x_tolerance if k[0] == "h" else join_y_tolerance)
        )
        for k, items in edge_groups
    )
    edges = list(itertools.chain(*edge_gen))
    return edges


def words_to_edges_h(
    words: T_obj_list, word_threshold: int = DEFAULT_MIN_WORDS_HORIZONTAL
) -> T_obj_list:
    """
    Find (imaginary) horizontal lines that connect the tops
    of at least `word_threshold` words.
    """
    by_top = utils.cluster_objects(words, itemgetter("top"), 1)
    large_clusters = filter(lambda x: len(x) >= word_threshold, by_top)
    rects = list(map(utils.objects_to_rect, large_clusters))
    if len(rects) == 0:
        return []
    min_x0 = min(map(itemgetter("x0"), rects))
    max_x1 = max(map(itemgetter("x1"), rects))

    edges = []
    for r in rects:
        edges += [
            # Top of text
            {
                "x0": min_x0,
                "x1": max_x1,
                "top": r["top"],
                "bottom": r["top"],
                "width": max_x1 - min_x0,
                "orientation": "h",
            },
            # For each detected row, we also add the 'bottom' line.  This will
            # generate extra edges, (some will be redundant with the next row
            # 'top' line), but this catches the last row of every table.
            {
                "x0": min_x0,
                "x1": max_x1,
                "top": r["bottom"],
                "bottom": r["bottom"],
                "width": max_x1 - min_x0,
                "orientation": "h",
            },
        ]

    return edges


def words_to_edges_v(
    words: T_obj_list, word_threshold: int = DEFAULT_MIN_WORDS_VERTICAL
) -> T_obj_list:
    """
    Find (imaginary) vertical lines that connect the left, right, or
    center of at least `word_threshold` words.
    """
    # Find words that share the same left, right, or centerpoints
    by_x0 = utils.cluster_objects(words, itemgetter("x0"), 1)
    by_x1 = utils.cluster_objects(words, itemgetter("x1"), 1)

    def get_center(word: T_obj) -> T_num:
        return float(word["x0"] + word["x1"]) / 2

    by_center = utils.cluster_objects(words, get_center, 1)
    clusters = by_x0 + by_x1 + by_center

    # Find the points that align with the most words
    sorted_clusters = sorted(clusters, key=lambda x: -len(x))
    large_clusters = filter(lambda x: len(x) >= word_threshold, sorted_clusters)

    # For each of those points, find the bboxes fitting all matching words
    bboxes = list(map(utils.objects_to_bbox, large_clusters))

    # Iterate through those bboxes, condensing overlapping bboxes
    condensed_bboxes: List[T_bbox] = []
    for bbox in bboxes:
        overlap = any(utils.get_bbox_overlap(bbox, c) for c in condensed_bboxes)
        if not overlap:
            condensed_bboxes.append(bbox)

    if len(condensed_bboxes) == 0:
        return []

    condensed_rects = map(utils.bbox_to_rect, condensed_bboxes)
    sorted_rects = list(sorted(condensed_rects, key=itemgetter("x0")))

    max_x1 = max(map(itemgetter("x1"), sorted_rects))
    min_top = min(map(itemgetter("top"), sorted_rects))
    max_bottom = max(map(itemgetter("bottom"), sorted_rects))

    return [
        {
            "x0": b["x0"],
            "x1": b["x0"],
            "top": min_top,
            "bottom": max_bottom,
            "height": max_bottom - min_top,
            "orientation": "v",
        }
        for b in sorted_rects
    ] + [
        {
            "x0": max_x1,
            "x1": max_x1,
            "top": min_top,
            "bottom": max_bottom,
            "height": max_bottom - min_top,
            "orientation": "v",
        }
    ]


def edges_to_intersections(
    edges: T_obj_list, x_tolerance: T_num = 1, y_tolerance: T_num = 1
) -> T_intersections:
    """
    Given a list of edges, return the points at which they intersect
    within `tolerance` pixels.
    """
    intersections: T_intersections = {}
    v_edges, h_edges = [
        list(filter(lambda x: x["orientation"] == o, edges)) for o in ("v", "h")
    ]
    for v in sorted(v_edges, key=itemgetter("x0", "top")):
        for h in sorted(h_edges, key=itemgetter("top", "x0")):
            if (
                (v["top"] <= (h["top"] + y_tolerance))
                and (v["bottom"] >= (h["top"] - y_tolerance))
                and (v["x0"] >= (h["x0"] - x_tolerance))
                and (v["x0"] <= (h["x1"] + x_tolerance))
            ):
                vertex = (v["x0"], h["top"])
                if vertex not in intersections:
                    intersections[vertex] = {"v": [], "h": []}
                intersections[vertex]["v"].append(v)
                intersections[vertex]["h"].append(h)
    return intersections


def intersections_to_cells(intersections: T_intersections) -> List[T_bbox]:
    """
    Given a list of points (`intersections`), return all rectangular "cells"
    that those points describe.

    `intersections` should be a dictionary with (x0, top) tuples as keys,
    and a list of edge objects as values. The edge objects should correspond
    to the edges that touch the intersection.
    """

    def edge_connects(p1: T_point, p2: T_point) -> bool:
        def edges_to_set(edges: T_obj_list) -> Set[T_bbox]:
            return set(map(utils.obj_to_bbox, edges))

        if p1[0] == p2[0]:
            common = edges_to_set(intersections[p1]["v"]).intersection(
                edges_to_set(intersections[p2]["v"])
            )
            if len(common):
                return True

        if p1[1] == p2[1]:
            common = edges_to_set(intersections[p1]["h"]).intersection(
                edges_to_set(intersections[p2]["h"])
            )
            if len(common):
                return True
        return False

    points = list(sorted(intersections.keys()))
    n_points = len(points)

    def find_smallest_cell(points: List[T_point], i: int) -> Optional[T_bbox]:
        if i == n_points - 1:
            return None
        pt = points[i]
        rest = points[i + 1 :]
        # Get all the points directly below and directly right
        below = [x for x in rest if x[0] == pt[0]]
        right = [x for x in rest if x[1] == pt[1]]
        for below_pt in below:
            if not edge_connects(pt, below_pt):
                continue

            for right_pt in right:
                if not edge_connects(pt, right_pt):
                    continue

                bottom_right = (right_pt[0], below_pt[1])

                if (
                    (bottom_right in intersections)
                    and edge_connects(bottom_right, right_pt)
                    and edge_connects(bottom_right, below_pt)
                ):

                    return (pt[0], pt[1], bottom_right[0], bottom_right[1])
        return None

    cell_gen = (find_smallest_cell(points, i) for i in range(len(points)))
    return list(filter(None, cell_gen))


def cells_to_tables(cells: List[T_bbox]) -> List[List[T_bbox]]:
    """
    Given a list of bounding boxes (`cells`), return a list of tables that
    hold those cells most simply (and contiguously).
    """

    def bbox_to_corners(bbox: T_bbox) -> Tuple[T_point, T_point, T_point, T_point]:
        x0, top, x1, bottom = bbox
        return ((x0, top), (x0, bottom), (x1, top), (x1, bottom))

    remaining_cells = list(cells)

    # Iterate through the cells found above, and assign them
    # to contiguous tables

    current_corners: Set[T_point] = set()
    current_cells: List[T_bbox] = []

    tables = []
    while len(remaining_cells):
        initial_cell_count = len(current_cells)
        for cell in list(remaining_cells):
            cell_corners = bbox_to_corners(cell)
            # If we're just starting a table ...
            if len(current_cells) == 0:
                # ... immediately assign it to the empty group
                current_corners |= set(cell_corners)
                current_cells.append(cell)
                remaining_cells.remove(cell)
            else:
                # How many corners does this table share with the current group?
                corner_count = sum(c in current_corners for c in cell_corners)

                # If touching on at least one corner...
                if corner_count > 0:
                    # ... assign it to the current group
                    current_corners |= set(cell_corners)
                    current_cells.append(cell)
                    remaining_cells.remove(cell)

        # If this iteration did not find any more cells to append...
        if len(current_cells) == initial_cell_count:
            # ... start a new cell group
            tables.append(list(current_cells))
            current_corners.clear()
            current_cells.clear()

    # Once we have exhausting the list of cells ...

    # ... and we have a cell group that has not been stored
    if len(current_cells):
        # ... store it.
        tables.append(list(current_cells))

    # Sort the tables top-to-bottom-left-to-right based on the value of the
    # topmost-and-then-leftmost coordinate of a table.
    _sorted = sorted(tables, key=lambda t: min((c[1], c[0]) for c in t))
    filtered = [t for t in _sorted if len(t) > 1]
    return filtered


class CellGroup(object):
    def __init__(self, cells: List[Optional[T_bbox]]):
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
    def __init__(self, page: "Page", cells: List[T_bbox]):
        self.page = page
        self.cells = cells

    @property
    def bbox(self) -> T_bbox:
        c = self.cells
        return (
            min(map(itemgetter(0), c)),
            min(map(itemgetter(1), c)),
            max(map(itemgetter(2), c)),
            max(map(itemgetter(3), c)),
        )

    @property
    def rows(self) -> List[Row]:
        _sorted = sorted(self.cells, key=itemgetter(1, 0))
        xs = list(sorted(set(map(itemgetter(0), self.cells))))
        rows = []
        for y, row_cells in itertools.groupby(_sorted, itemgetter(1)):
            xdict = {cell[0]: cell for cell in row_cells}
            row = Row([xdict.get(x) for x in xs])
            rows.append(row)
        return rows

    def extract(
        self,
        x_tolerance: T_num = utils.DEFAULT_X_TOLERANCE,
        y_tolerance: T_num = utils.DEFAULT_Y_TOLERANCE,
    ) -> List[List[Optional[str]]]:

        chars = self.page.chars
        table_arr = []

        def char_in_bbox(char: T_obj, bbox: T_bbox) -> bool:
            v_mid = (char["top"] + char["bottom"]) / 2
            h_mid = (char["x0"] + char["x1"]) / 2
            x0, top, x1, bottom = bbox
            return bool(
                (h_mid >= x0) and (h_mid < x1) and (v_mid >= top) and (v_mid < bottom)
            )

        for row in self.rows:
            arr = []
            row_chars = [char for char in chars if char_in_bbox(char, row.bbox)]

            for cell in row.cells:
                if cell is None:
                    cell_text = None
                else:
                    cell_chars = [
                        char for char in row_chars if char_in_bbox(char, cell)
                    ]

                    if len(cell_chars):
                        cell_text = utils.extract_text(
                            cell_chars,
                            x_tolerance=x_tolerance,
                            y_tolerance=y_tolerance,
                        ).strip()
                    else:
                        cell_text = ""
                arr.append(cell_text)
            table_arr.append(arr)

        return table_arr


TABLE_STRATEGIES = ["lines", "lines_strict", "text", "explicit"]
NON_NEGATIVE_SETTINGS = [
    "snap_tolerance",
    "snap_x_tolerance",
    "snap_y_tolerance",
    "join_tolerance",
    "join_x_tolerance",
    "join_y_tolerance",
    "edge_min_length",
    "min_words_vertical",
    "min_words_horizontal",
    "text_tolerance",
    "text_x_tolerance",
    "text_y_tolerance",
    "intersection_tolerance",
    "intersection_x_tolerance",
    "intersection_y_tolerance",
]


class UnsetFloat(float):
    pass


UNSET = UnsetFloat(0)


@dataclass
class TableSettings:
    vertical_strategy: str = "lines"
    horizontal_strategy: str = "lines"
    explicit_vertical_lines: Optional[List[Union[T_obj, T_num]]] = None
    explicit_horizontal_lines: Optional[List[Union[T_obj, T_num]]] = None
    snap_tolerance: T_num = DEFAULT_SNAP_TOLERANCE
    snap_x_tolerance: T_num = UNSET
    snap_y_tolerance: T_num = UNSET
    join_tolerance: T_num = DEFAULT_JOIN_TOLERANCE
    join_x_tolerance: T_num = UNSET
    join_y_tolerance: T_num = UNSET
    edge_min_length: T_num = 3
    min_words_vertical: int = DEFAULT_MIN_WORDS_VERTICAL
    min_words_horizontal: int = DEFAULT_MIN_WORDS_HORIZONTAL
    keep_blank_chars: bool = False
    text_tolerance: T_num = 3
    text_x_tolerance: T_num = UNSET
    text_y_tolerance: T_num = UNSET
    intersection_tolerance: T_num = 3
    intersection_x_tolerance: T_num = UNSET
    intersection_y_tolerance: T_num = UNSET

    def __post_init__(self) -> "TableSettings":
        """Clean up user-provided table settings.

        Validates that the table settings provided consists of acceptable values and
        returns a cleaned up version. The cleaned up version fills out the missing
        values with the default values in the provided settings.

        TODO: Can be further used to validate that the values are of the correct
            type. For example, raising a value error when a non-boolean input is
            provided for the key ``keep_blank_chars``.

        :param table_settings: User-provided table settings.
        :returns: A cleaned up version of the user-provided table settings.
        :raises ValueError: When an unrecognised key is provided.
        """

        for setting in NON_NEGATIVE_SETTINGS:
            if (getattr(self, setting) or 0) < 0:
                raise ValueError(f"Table setting '{setting}' cannot be negative")

        for orientation in ["horizontal", "vertical"]:
            strategy = getattr(self, orientation + "_strategy")
            if strategy not in TABLE_STRATEGIES:
                raise ValueError(
                    f"{orientation}_strategy must be one of"
                    f'{{{",".join(TABLE_STRATEGIES)}}}'
                )

        for attr, fallback in [
            ("text_x_tolerance", "text_tolerance"),
            ("text_y_tolerance", "text_tolerance"),
            ("snap_x_tolerance", "snap_tolerance"),
            ("snap_y_tolerance", "snap_tolerance"),
            ("join_x_tolerance", "join_tolerance"),
            ("join_y_tolerance", "join_tolerance"),
            ("intersection_x_tolerance", "intersection_tolerance"),
            ("intersection_y_tolerance", "intersection_tolerance"),
        ]:
            if getattr(self, attr) is UNSET:
                setattr(self, attr, getattr(self, fallback))

        return self

    @classmethod
    def resolve(cls, settings: Optional[T_table_settings]) -> "TableSettings":
        if settings is None:
            return cls()
        elif isinstance(settings, cls):
            return settings
        elif isinstance(settings, dict):
            return cls(**settings)
        else:
            raise ValueError(f"Cannot resolve settings: {settings}")


class TableFinder(object):
    """
    Given a PDF page, find plausible table structures.

    Largely borrowed from Anssi Nurminen's master's thesis:
    http://dspace.cc.tut.fi/dpub/bitstream/handle/123456789/21520/Nurminen.pdf?sequence=3

    ... and inspired by Tabula:
    https://github.com/tabulapdf/tabula-extractor/issues/16
    """

    def __init__(self, page: "Page", settings: Optional[T_table_settings] = None):
        self.page = page
        self.settings = TableSettings.resolve(settings)
        self.edges = self.get_edges()
        self.intersections = edges_to_intersections(
            self.edges,
            self.settings.intersection_x_tolerance,
            self.settings.intersection_y_tolerance,
        )
        self.cells = intersections_to_cells(self.intersections)
        self.tables = [
            Table(self.page, cell_group) for cell_group in cells_to_tables(self.cells)
        ]

    def get_edges(self) -> T_obj_list:
        settings = self.settings

        for orientation in ["vertical", "horizontal"]:
            strategy = getattr(settings, orientation + "_strategy")
            if strategy == "explicit":
                lines = getattr(settings, "explicit_" + orientation + "_lines")
                if len(lines) < 2:
                    raise ValueError(
                        f"If {orientation}_strategy == 'explicit', "
                        f"explicit_{orientation}_lines "
                        f"must be specified as a list/tuple of two or more "
                        f"floats/ints."
                    )

        v_strat = settings.vertical_strategy
        h_strat = settings.horizontal_strategy

        if v_strat == "text" or h_strat == "text":
            words = self.page.extract_words(
                x_tolerance=settings.text_x_tolerance,
                y_tolerance=settings.text_y_tolerance,
                keep_blank_chars=settings.keep_blank_chars,
            )

        v_explicit = []
        for desc in settings.explicit_vertical_lines or []:
            if isinstance(desc, dict):
                for e in utils.obj_to_edges(desc):
                    if e["orientation"] == "v":
                        v_explicit.append(e)
            else:
                v_explicit.append(
                    {
                        "x0": desc,
                        "x1": desc,
                        "top": self.page.bbox[1],
                        "bottom": self.page.bbox[3],
                        "height": self.page.bbox[3] - self.page.bbox[1],
                        "orientation": "v",
                    }
                )

        if v_strat == "lines":
            v_base = utils.filter_edges(self.page.edges, "v")
        elif v_strat == "lines_strict":
            v_base = utils.filter_edges(self.page.edges, "v", edge_type="line")
        elif v_strat == "text":
            v_base = words_to_edges_v(words, word_threshold=settings.min_words_vertical)
        elif v_strat == "explicit":
            v_base = []

        v = v_base + v_explicit

        h_explicit = []
        for desc in settings.explicit_horizontal_lines or []:
            if isinstance(desc, dict):
                for e in utils.obj_to_edges(desc):
                    if e["orientation"] == "h":
                        h_explicit.append(e)
            else:
                h_explicit.append(
                    {
                        "x0": self.page.bbox[0],
                        "x1": self.page.bbox[2],
                        "width": self.page.bbox[2] - self.page.bbox[0],
                        "top": desc,
                        "bottom": desc,
                        "orientation": "h",
                    }
                )

        if h_strat == "lines":
            h_base = utils.filter_edges(self.page.edges, "h")
        elif h_strat == "lines_strict":
            h_base = utils.filter_edges(self.page.edges, "h", edge_type="line")
        elif h_strat == "text":
            h_base = words_to_edges_h(
                words, word_threshold=settings.min_words_horizontal
            )
        elif h_strat == "explicit":
            h_base = []

        h = h_base + h_explicit

        edges = list(v) + list(h)

        edges = merge_edges(
            edges,
            snap_x_tolerance=settings.snap_x_tolerance,
            snap_y_tolerance=settings.snap_y_tolerance,
            join_x_tolerance=settings.join_x_tolerance,
            join_y_tolerance=settings.join_y_tolerance,
        )

        return utils.filter_edges(edges, min_length=settings.edge_min_length)
