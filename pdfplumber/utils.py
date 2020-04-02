from pdfminer.utils import PDFDocEncoding
from pdfminer.psparser import PSLiteral
try:
    from cdecimal import Decimal, ROUND_HALF_UP
except ImportError:
    from decimal import Decimal, ROUND_HALF_UP
import numbers
from operator import itemgetter
import itertools
import six

if six.PY3:
    from functools import lru_cache as cache
else:
    # Python 2 has no lru_cache, so defining as a no-op
    def cache(**kwargs):
        def decorator(fn):
            return fn
        return decorator

DEFAULT_X_TOLERANCE = 3
DEFAULT_Y_TOLERANCE = 3

def cluster_list(xs, tolerance=0):
    tolerance = decimalize(tolerance)
    if tolerance == 0: return [ [x] for x in sorted(xs) ]
    if len(xs) < 2: return [ [x] for x in sorted(xs) ]
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

    nested_tuples = [ [ (val, i) for val in value_cluster ]
        for i, value_cluster in enumerate(clusters) ]

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

    cluster_tuples = sorted(((obj, cluster_dict.get(attr_getter(obj)))
        for obj in objs), key=get_1)

    grouped = itertools.groupby(cluster_tuples, key=get_1)

    clusters = [ list(map(get_0, v))
        for k, v in grouped ]

    return clusters

def decode_text(s):
    """
    Decodes a PDFDocEncoding string to Unicode.
    Adds py3 compatibility to pdfminer's version.
    """
    if type(s) == bytes and s.startswith(b'\xfe\xff'):
        return six.text_type(s[2:], 'utf-16be', 'ignore')
    else:
        ords = (ord(c) if type(c) == str else c for c in s)
        return ''.join(PDFDocEncoding[o] for o in ords)

def decode_psl_list(_list):
    return [ decode_text(value.name) if isinstance(value, PSLiteral) else value
        for value in _list ]

@cache(maxsize = int(10e4))
def _decimalize(v, q = None):
    # If already a decimal, just return itself
    if isinstance(v, Decimal):
        return v

    # If tuple/list passed, bulk-convert
    elif isinstance(v, (tuple, list)):
        return type(v)(decimalize(x, q) for x in v)

    # Convert int-like
    elif isinstance(v, numbers.Integral):
        return Decimal(int(v))

    # Convert float-like
    elif isinstance(v, numbers.Real):
        if q != None:
            return Decimal(repr(v)).quantize(Decimal(repr(q)),
                rounding=ROUND_HALF_UP)
        else:
            return Decimal(repr(v))
    else:
        raise ValueError("Cannot convert {0} to Decimal.".format(v))

def decimalize(v, q = None):
    # If tuple/list passed, bulk-convert
    if isinstance(v, (tuple, list)):
        return type(v)(decimalize(x, q) for x in v)
    else:
        return _decimalize(v, q)

def is_dataframe(collection):
    cls = collection.__class__
    name = ".".join([ cls.__module__, cls.__name__ ])
    return name == "pandas.core.frame.DataFrame"

def to_list(collection):
    if is_dataframe(collection):
        return collection.to_dict("records")
    else:
        return list(collection)

def collate_line(line_chars, tolerance=DEFAULT_X_TOLERANCE):
    tolerance = decimalize(tolerance)
    coll = ""
    last_x1 = None
    for char in sorted(line_chars, key=itemgetter("x0")):
        if (last_x1 != None) and (char["x0"] > (last_x1 + tolerance)):
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
    return {
        "x0": bbox[0],
        "top": bbox[1],
        "x1": bbox[2],
        "bottom": bbox[3]
    }



def extract_words(chars,
    x_tolerance=DEFAULT_X_TOLERANCE,
    y_tolerance=DEFAULT_Y_TOLERANCE,
    keep_blank_chars=False,
    horizontal_ltr = True, # Should words be read left-to-right?
    vertical_ttb = True, # Should vertical words be read top-to-bottom?
    ):

    x_tolerance = decimalize(x_tolerance)
    y_tolerance = decimalize(y_tolerance)

    def process_word_chars(chars, upright):
        x0, top, x1, bottom = objects_to_bbox(chars)

        if upright:
            if horizontal_ltr:
                sorted_chars = chars
            else:
                sorted_chars = sorted(chars, key = lambda x: -x["x1"])
        else:
            if vertical_ttb:
                sorted_chars = sorted(chars, key = itemgetter("doctop"))
            else:
                sorted_chars = sorted(chars, key = lambda x: -x["bottom"])

        return {
            "x0": x0,
            "x1": x1,
            "top": top,
            "bottom": bottom,
            "upright": upright,
            "text": "".join(map(itemgetter("text"), sorted_chars))
        }

    def get_line_words(chars, upright, tolerance=DEFAULT_X_TOLERANCE):
        get_text = itemgetter("text")
        min_key = "x0" if upright else "top"
        max_key = "x1" if upright else "bottom"

        chars_sorted = sorted(chars, key=itemgetter(min_key))

        words = []
        current_word = []

        for char in chars_sorted:
            if not keep_blank_chars and get_text(char).isspace():
                if len(current_word) > 0:
                    words.append(current_word)
                    current_word = []
                else: pass
            elif len(current_word) == 0:
                current_word.append(char)
            else:
                last_char = current_word[-1]
                if char[min_key] > (last_char[max_key] + tolerance):
                    words.append(current_word)
                    current_word = []
                current_word.append(char)

        if len(current_word) > 0:
            words.append(current_word)

        return [ process_word_chars(chars, upright)
            for chars in words ]

    chars_by_upright = { 1: [], 0: [] }
    words = []
    for char in to_list(chars):
        chars_by_upright[char.get("upright", 1)].append(char)

    for upright, char_group in chars_by_upright.items():
        clusters = cluster_objects(
            char_group,
            "doctop" if upright else "x0",
            y_tolerance, # Still use y-tolerance here, even for vertical words
        )

        for line_chars in clusters:
            words += get_line_words(line_chars, upright, tolerance = x_tolerance)

    return words

def extract_text(chars,
    x_tolerance=DEFAULT_X_TOLERANCE,
    y_tolerance=DEFAULT_Y_TOLERANCE):

    if len(chars) == 0:
        return None

    chars = to_list(chars)
    doctop_clusters = cluster_objects(chars, "doctop", y_tolerance)

    lines = (collate_line(line_chars, x_tolerance)
        for line_chars in doctop_clusters)

    coll = "\n".join(lines)
    return coll

collate_chars = extract_text

def filter_objects(objs, fn):
    if isinstance(objs, dict):
        return dict((k, filter_objects(v, fn))
            for k,v in objs.items())

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

def clip_obj(obj, bbox):
    bbox = decimalize(bbox)

    overlap = get_bbox_overlap(obj_to_bbox(obj), bbox)
    if overlap is None: return None

    dims = bbox_to_rect(overlap)
    copy = dict(obj)

    for attr in [ "x0", "top", "x1", "bottom" ]:
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
    matching = [ obj for obj in objs
        if get_bbox_overlap(obj_to_bbox(obj), bbox) is not None ]
    return initial_type(matching)

def within_bbox(objs, bbox):
    """
    Filters objs to only those fully within the bbox
    """
    if isinstance(objs, dict):
        return dict((k, within_bbox(v, bbox))
            for k,v in objs.items())

    initial_type = type(objs)
    objs = to_list(objs)
    matching = [ obj for obj in objs
        if get_bbox_overlap(obj_to_bbox(obj), bbox) == obj_to_bbox(obj) ]
    return initial_type(matching)

def crop_to_bbox(objs, bbox):
    """
    Filters objs to only those intersecting the bbox,
    and crops the extent of the objects to the bbox.
    """
    if isinstance(objs, dict):
        return dict((k, crop_to_bbox(v, bbox))
            for k,v in objs.items())

    initial_type = type(objs)
    objs = to_list(objs)
    cropped = list(filter(None, (clip_obj(obj, bbox) for obj in objs)))
    return initial_type(cropped)

def move_object(obj, axis, value):
    assert(axis in ("h", "v"))
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
            new_items += [ ("doctop", obj["doctop"] + value) ]
        if "y0" in obj:
            new_items += [
                ("y0", obj["y0"] - value),
                ("y1", obj["y1"] - value),
            ]
    return obj.__class__(tuple(obj.items()) + tuple(new_items))

def resize_object(obj, key, value):
    assert(key in ("x0", "x1", "top", "bottom"))
    old_value = obj[key]
    diff = value - old_value
    if key in ("x0", "x1"):
        if key == "x0":
            assert(value <= obj["x1"])
        else:
            assert(value >= obj["x0"])
        new_items = (
            (key, value),
            ("width", obj["width"] + diff),
        )
    if key == "top":
        assert(value <= obj["bottom"])
        new_items = [
            (key, value),
            ("doctop", obj["doctop"] + diff),
            ("height", obj["height"] - diff),
        ]
        if "y1" in obj:
            new_items += [
                ("y1", obj["y1"] - diff),
            ]
    if key == "bottom":
        assert(value >= obj["top"])
        new_items = [
            (key, value),
            ("height", obj["height"] + diff),
        ]
        if "y0" in obj:
            new_items += [
                ("y0", obj["y0"] - diff),
            ]
    return obj.__class__(tuple(obj.items()) + tuple(new_items))

def curve_to_edges(curve):
    point_pairs = zip(curve["points"], curve["points"][1:]) 
    return [ {
        "x0": min(p0[0], p1[0]),
        "x1": max(p0[0], p1[0]),
        "top": min(p0[1], p1[1]),
        "doctop": min(p0[1], p1[1]) + (curve["doctop"] - curve["top"]),
        "bottom": max(p0[1], p1[1]),
        "width": abs(p0[0] - p1[0]),
        "height": abs(p0[1] - p1[1]),
        "orientation": "v" if p0[0] == p1[0] else ("h" if p0[1] == p1[1] else None)
    } for p0, p1 in point_pairs ]

def rect_to_edges(rect):
    top, bottom, left, right = [ dict(rect) for x in range(4) ]
    top.update({
        "object_type": "rect_edge",
        "height": decimalize(0),
        "y0": rect["y1"],
        "bottom": rect["top"],
        "orientation": "h"
    })
    bottom.update({
        "object_type": "rect_edge",
        "height": decimalize(0),
        "y1": rect["y0"],
        "top": rect["top"] + rect["height"],
        "doctop": rect["doctop"] + rect["height"],
        "orientation": "h"
    })
    left.update({
        "object_type": "rect_edge",
        "width": decimalize(0),
        "x1": rect["x0"],
        "orientation": "v"
    })
    right.update({
        "object_type": "rect_edge",
        "width": decimalize(0),
        "x0": rect["x1"],
        "orientation": "v"
    })
    return [ top, bottom, left, right ]

def line_to_edge(line):
    edge = dict(line)
    edge["orientation"] = "h" if (line["top"] == line["bottom"]) else "v"
    return edge

def obj_to_edges(obj):
    return {
        "line": lambda x: [ line_to_edge(x) ],
        "rect": rect_to_edges,
        "curve": curve_to_edges,
    }[obj["object_type"]](obj)

def filter_edges(edges, orientation=None,
    edge_type=None,
    min_length=1):

    if orientation not in ("v", "h", None):
        raise ValueError("Orientation must be 'v' or 'h'")

    def test(e):
        dim = "height" if e["orientation"] == "v" else "width"
        et = (e["object_type"] == edge_type if edge_type != None else True)
        return et & (
            (True if orientation == None else (e["orientation"] == orientation)) & 
            (e[dim] >= min_length)
        )

    edges = filter(test, edges)
    return list(edges)
