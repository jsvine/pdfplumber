from pdfminer.utils import PDFDocEncoding
from pdfminer.psparser import PSLiteral
from pdfminer.pdftypes import PDFObjRef
from decimal import Decimal, ROUND_HALF_UP
import numbers
from operator import itemgetter, gt, lt, add, sub
import itertools
from functools import lru_cache as cache

DEFAULT_X_TOLERANCE = 3
DEFAULT_Y_TOLERANCE = 3


def cluster_list(xs, tolerance=0):
    tolerance = decimalize(tolerance)
    if tolerance == Decimal(0):
        return [[x] for x in sorted(xs)]
    if len(xs) < 2:
        return [[x] for x in sorted(xs)]
    groups = []
    xs = list(sorted(xs))
    current_group = [xs[0]]
    last = xs[0]
    for x in xs[1:]:
        if x <= (last + tolerance):
            current_group.append(x)
        else:
            groups.append(current_group)
            current_group = [x]
        last = x
    groups.append(current_group)
    return groups


def make_cluster_dict(values, tolerance):
    tolerance = decimalize(tolerance)
    clusters = cluster_list(set(values), tolerance)

    nested_tuples = [
        [(val, i) for val in value_cluster] for i, value_cluster in enumerate(clusters)
    ]

    cluster_dict = dict(itertools.chain(*nested_tuples))
    return cluster_dict


def cluster_objects(objs, attr, tolerance):
    if isinstance(attr, (str, int)):
        attr_getter = itemgetter(attr)
    else:
        attr_getter = attr
    objs = to_list(objs)
    values = map(attr_getter, objs)
    cluster_dict = make_cluster_dict(values, tolerance)

    get_0, get_1 = itemgetter(0), itemgetter(1)

    cluster_tuples = sorted(
        ((obj, cluster_dict.get(attr_getter(obj))) for obj in objs), key=get_1
    )

    grouped = itertools.groupby(cluster_tuples, key=get_1)

    clusters = [list(map(get_0, v)) for k, v in grouped]

    return clusters


def decode_text(s):
    """
    Decodes a PDFDocEncoding string to Unicode.
    Adds py3 compatibility to pdfminer's version.
    """
    if type(s) == bytes and s.startswith(b"\xfe\xff"):
        return str(s[2:], "utf-16be", "ignore")
    else:
        ords = (ord(c) if type(c) == str else c for c in s)
        return "".join(PDFDocEncoding[o] for o in ords)


def decode_psl_list(_list):
    return [
        decode_text(value.name) if isinstance(value, PSLiteral) else value
        for value in _list
    ]


def resolve(x):
    if type(x) == PDFObjRef:
        return x.resolve()
    else:
        return x


def get_dict_type(d):
    if type(d) is not dict:
        return None
    t = d.get("Type")
    if type(t) is PSLiteral:
        return decode_text(t.name)
    else:
        return t


def resolve_all(x):
    """
    Recursively resolves the given object and all the internals.
    """
    t = type(x)
    if t == PDFObjRef:
        resolved = x.resolve()

        # Avoid infinite recursion
        if get_dict_type(resolved) == "Page":
            return x

        return resolve_all(resolved)
    elif t in (list, tuple):
        return t(resolve_all(v) for v in x)
    elif t == dict:
        if get_dict_type(x) == "Annot":
            exceptions = ["Parent"]
        else:
            exceptions = []
        return dict((k, v if k in exceptions else resolve_all(v)) for k, v in x.items())
    else:
        return x


@cache(maxsize=int(10e4))
def _decimalize(v, q=None):
    # Convert int-like
    if isinstance(v, numbers.Integral):
        return Decimal(int(v))

    # Convert float-like
    elif isinstance(v, numbers.Real):
        if q is not None:
            return Decimal(repr(v)).quantize(Decimal(repr(q)), rounding=ROUND_HALF_UP)
        else:
            return Decimal(repr(v))
    else:
        raise ValueError(f"Cannot convert {v} to Decimal.")


def decimalize(v, q=None):
    # If already a decimal, just return itself
    if type(v) == Decimal:
        return v

    # If tuple/list passed, bulk-convert
    if isinstance(v, (tuple, list)):
        return type(v)(decimalize(x, q) for x in v)
    else:
        return _decimalize(v, q)


def is_dataframe(collection):
    cls = collection.__class__
    name = ".".join([cls.__module__, cls.__name__])
    return name == "pandas.core.frame.DataFrame"


def to_list(collection):
    if is_dataframe(collection):
        return collection.to_dict("records")  # pragma: nocover
    else:
        return list(collection)


def drop_duplicates_in_line_chars(line_chars,
                                  tolerance=DEFAULT_X_TOLERANCE,
                                  horizontal=True,  # Should words be read left-to-right or top-to-bottom
                                  ):
    """drop duplicates of char-pairs with same text and font type
    """
    if len(line_chars) < 2:
        return line_chars

    tolerance = decimalize(tolerance)
    coll = []
    last_char = None
    min_key = 'x0' if horizontal else 'y0'

    def compare_char_style(char_1, char_2):
        keys = ['text', 'fontname', 'width', 'height', 'size']
        return all([char_1.get(key) == char_2.get(key) for key in keys])

    for char in sorted(line_chars, key=itemgetter(min_key)):
        if not coll or not (
                compare_char_style(last_char, char) and last_char.get(min_key) + tolerance > char.get(min_key)):
            coll.append(char)
            last_char = char

    return coll


def collate_line(line_chars, tolerance=DEFAULT_X_TOLERANCE, drop_duplicates=True):
    if drop_duplicates:
        line_chars = drop_duplicates_in_line_chars(line_chars, tolerance)
    tolerance = decimalize(tolerance)
    coll = ""
    last_x1 = None
    for char in sorted(line_chars, key=itemgetter("x0")):
        if (last_x1 is not None) and (char["x0"] > (last_x1 + tolerance)):
            coll += " "
        last_x1 = char["x1"]
        coll += char["text"]
    return coll


def objects_to_rect(objects):
    return {
        "x0": min(map(itemgetter("x0"), objects)),
        "x1": max(map(itemgetter("x1"), objects)),
        "top": min(map(itemgetter("top"), objects)),
        "bottom": max(map(itemgetter("bottom"), objects)),
    }


def objects_to_bbox(objects):
    return (
        min(map(itemgetter("x0"), objects)),
        min(map(itemgetter("top"), objects)),
        max(map(itemgetter("x1"), objects)),
        max(map(itemgetter("bottom"), objects)),
    )


obj_to_bbox = itemgetter("x0", "top", "x1", "bottom")


def bbox_to_rect(bbox):
    return {"x0": bbox[0], "top": bbox[1], "x1": bbox[2], "bottom": bbox[3]}


def extract_words(
    chars,
    x_tolerance=DEFAULT_X_TOLERANCE,
    y_tolerance=DEFAULT_Y_TOLERANCE,
    keep_blank_chars=False,
    horizontal_ltr=True,  # Should words be read left-to-right?
    vertical_ttb=True,  # Should vertical words be read top-to-bottom?
    drop_duplicates=True,  # Should drop duplicates pair in the same line?
):

    x_tolerance = decimalize(x_tolerance)
    y_tolerance = decimalize(y_tolerance)

    def process_word_chars(chars, upright):
        x0, top, x1, bottom = objects_to_bbox(chars)

        return {
            "x0": x0,
            "x1": x1,
            "top": top,
            "bottom": bottom,
            "upright": upright,
            "text": "".join(map(itemgetter("text"), chars)),
        }

    def get_line_words(chars, upright, tolerance):
        get_text = itemgetter("text")
        if upright:
            min_key, max_key = ("x0", "x1") if horizontal_ltr else ("x1", "x0")
        else:
            min_key, max_key = ("top", "bottom") if vertical_ttb else ("bottom", "top")

        words = []
        current_word = []

        asc_order = (upright and horizontal_ltr) or (not upright and vertical_ttb)

        comp_fn = gt if asc_order else lt
        tol_fn = add if asc_order else sub

        def sort_key(x):
            return tol_fn(0, x[min_key])

        # remove duplicates
        if drop_duplicates:
            chars = drop_duplicates_in_line_chars(chars, tolerance, horizontal_ltr)

        sorted_chars = sorted(chars, key=sort_key)

        for char in sorted_chars:
            if not keep_blank_chars and get_text(char).isspace():
                if len(current_word) > 0:
                    words.append(current_word)
                    current_word = []
                else:
                    pass
            elif len(current_word) == 0:
                current_word.append(char)
            else:
                last_char = current_word[-1]
                prev_pos = tol_fn(last_char[max_key], tolerance)
                if comp_fn(char[min_key], prev_pos):
                    words.append(current_word)
                    current_word = []
                current_word.append(char)

        if len(current_word) > 0:
            words.append(current_word)

        return [process_word_chars(chars, upright) for chars in words]

    chars_by_upright = {1: [], 0: []}
    words = []
    for char in to_list(chars):
        chars_by_upright[char.get("upright", 1)].append(char)

    for upright, char_group in chars_by_upright.items():
        clusters = cluster_objects(
            char_group,
            "doctop" if upright else "x0",
            y_tolerance,  # Still use y-tolerance here, even for vertical words
        )

        for line_chars in clusters:
            words += get_line_words(line_chars, upright, tolerance=x_tolerance)

    return words


def extract_text(
        chars, x_tolerance=DEFAULT_X_TOLERANCE, y_tolerance=DEFAULT_Y_TOLERANCE, drop_duplicates=True):

    if len(chars) == 0:
        return None

    chars = to_list(chars)
    doctop_clusters = cluster_objects(chars, "doctop", y_tolerance)

    lines = (collate_line(line_chars, x_tolerance, drop_duplicates) for line_chars in doctop_clusters)

    coll = "\n".join(lines)
    return coll


collate_chars = extract_text


def filter_objects(objs, fn):
    if isinstance(objs, dict):
        return dict((k, filter_objects(v, fn)) for k, v in objs.items())

    initial_type = type(objs)
    objs = to_list(objs)
    filtered = filter(fn, objs)

    return initial_type(filtered)


def get_bbox_overlap(a, b):
    a_left, a_top, a_right, a_bottom = decimalize(a)
    b_left, b_top, b_right, b_bottom = decimalize(b)
    o_left = max(a_left, b_left)
    o_right = min(a_right, b_right)
    o_bottom = min(a_bottom, b_bottom)
    o_top = max(a_top, b_top)
    o_width = o_right - o_left
    o_height = o_bottom - o_top
    if o_height >= 0 and o_width >= 0 and o_height + o_width > 0:
        return (o_left, o_top, o_right, o_bottom)
    else:
        return None


def calculate_area(bbox):
    left, top, right, bottom = bbox
    if left > right or top > bottom:
        raise ValueError(f"{bbox} has a negative width or height.")
    return (right - left) * (bottom - top)


def clip_obj(obj, bbox):
    bbox = decimalize(bbox)

    overlap = get_bbox_overlap(obj_to_bbox(obj), bbox)
    if overlap is None:
        return None

    dims = bbox_to_rect(overlap)
    copy = dict(obj)

    for attr in ["x0", "top", "x1", "bottom"]:
        copy[attr] = dims[attr]

    if dims["top"] != obj["bottom"] or dims["top"] != obj["bottom"]:
        diff = dims["top"] - obj["top"]
        copy["doctop"] = obj["doctop"] + diff

    copy["width"] = copy["x1"] - copy["x0"]
    copy["height"] = copy["bottom"] - copy["top"]

    return copy


def intersects_bbox(objs, bbox):
    """
    Filters objs to only those intersecting the bbox
    """
    initial_type = type(objs)
    objs = to_list(objs)
    matching = [
        obj for obj in objs if get_bbox_overlap(obj_to_bbox(obj), bbox) is not None
    ]
    return initial_type(matching)


def within_bbox(objs, bbox):
    """
    Filters objs to only those fully within the bbox
    """
    if isinstance(objs, dict):
        return dict((k, within_bbox(v, bbox)) for k, v in objs.items())

    initial_type = type(objs)
    objs = to_list(objs)
    matching = [
        obj
        for obj in objs
        if get_bbox_overlap(obj_to_bbox(obj), bbox) == obj_to_bbox(obj)
    ]
    return initial_type(matching)


def crop_to_bbox(objs, bbox):
    """
    Filters objs to only those intersecting the bbox,
    and crops the extent of the objects to the bbox.
    """
    if isinstance(objs, dict):
        return dict((k, crop_to_bbox(v, bbox)) for k, v in objs.items())

    initial_type = type(objs)
    objs = to_list(objs)
    cropped = list(filter(None, (clip_obj(obj, bbox) for obj in objs)))
    return initial_type(cropped)


def move_object(obj, axis, value):
    assert axis in ("h", "v")
    if axis == "h":
        new_items = (
            ("x0", obj["x0"] + value),
            ("x1", obj["x1"] + value),
        )
    if axis == "v":
        new_items = [
            ("top", obj["top"] + value),
            ("bottom", obj["bottom"] + value),
        ]
        if "doctop" in obj:
            new_items += [("doctop", obj["doctop"] + value)]
        if "y0" in obj:
            new_items += [
                ("y0", obj["y0"] - value),
                ("y1", obj["y1"] - value),
            ]
    return obj.__class__(tuple(obj.items()) + tuple(new_items))


def snap_objects(objs, attr, tolerance):
    axis = {"x0": "h", "x1": "h", "top": "v", "bottom": "v"}[attr]
    clusters = cluster_objects(objs, attr, tolerance)
    avgs = [sum(map(itemgetter(attr), objs)) / len(objs) for objs in clusters]
    snapped_clusters = [
        [move_object(obj, axis, avg - obj[attr]) for obj in cluster]
        for cluster, avg in zip(clusters, avgs)
    ]
    return list(itertools.chain(*snapped_clusters))


def resize_object(obj, key, value):
    assert key in ("x0", "x1", "top", "bottom")
    old_value = obj[key]
    diff = value - old_value
    new_items = [
        (key, value),
    ]
    if key == "x0":
        assert value <= obj["x1"]
        new_items.append(("width", obj["x1"] - value))
    elif key == "x1":
        assert value >= obj["x0"]
        new_items.append(("width", value - obj["x0"]))
    elif key == "top":
        assert value <= obj["bottom"]
        new_items.append(("doctop", obj["doctop"] + diff))
        new_items.append(("height", obj["height"] - diff))
        if "y1" in obj:
            new_items.append(("y1", obj["y1"] - diff))
    elif key == "bottom":
        assert value >= obj["top"]
        new_items.append(("height", obj["height"] + diff))
        if "y0" in obj:
            new_items.append(("y0", obj["y0"] - diff))
    return obj.__class__(tuple(obj.items()) + tuple(new_items))


def curve_to_edges(curve):
    point_pairs = zip(curve["points"], curve["points"][1:])
    return [
        {
            "x0": min(p0[0], p1[0]),
            "x1": max(p0[0], p1[0]),
            "top": min(p0[1], p1[1]),
            "doctop": min(p0[1], p1[1]) + (curve["doctop"] - curve["top"]),
            "bottom": max(p0[1], p1[1]),
            "width": abs(p0[0] - p1[0]),
            "height": abs(p0[1] - p1[1]),
            "orientation": "v" if p0[0] == p1[0] else ("h" if p0[1] == p1[1] else None),
        }
        for p0, p1 in point_pairs
    ]


def rect_to_edges(rect):
    top, bottom, left, right = [dict(rect) for x in range(4)]
    top.update(
        {
            "object_type": "rect_edge",
            "height": decimalize(0),
            "y0": rect["y1"],
            "bottom": rect["top"],
            "orientation": "h",
        }
    )
    bottom.update(
        {
            "object_type": "rect_edge",
            "height": decimalize(0),
            "y1": rect["y0"],
            "top": rect["top"] + rect["height"],
            "doctop": rect["doctop"] + rect["height"],
            "orientation": "h",
        }
    )
    left.update(
        {
            "object_type": "rect_edge",
            "width": decimalize(0),
            "x1": rect["x0"],
            "orientation": "v",
        }
    )
    right.update(
        {
            "object_type": "rect_edge",
            "width": decimalize(0),
            "x0": rect["x1"],
            "orientation": "v",
        }
    )
    return [top, bottom, left, right]


def line_to_edge(line):
    edge = dict(line)
    edge["orientation"] = "h" if (line["top"] == line["bottom"]) else "v"
    return edge


def obj_to_edges(obj):
    return {
        "line": lambda x: [line_to_edge(x)],
        "rect": rect_to_edges,
        "rect_edge": rect_to_edges,
        "curve": curve_to_edges,
    }[obj["object_type"]](obj)


def filter_edges(edges, orientation=None, edge_type=None, min_length=1):

    if orientation not in ("v", "h", None):
        raise ValueError("Orientation must be 'v' or 'h'")

    def test(e):
        dim = "height" if e["orientation"] == "v" else "width"
        et_correct = e["object_type"] == edge_type if edge_type is not None else True
        orient_correct = orientation is None or e["orientation"] == orientation
        return et_correct and orient_correct and (e[dim] >= min_length)

    edges = filter(test, edges)
    return list(edges)
