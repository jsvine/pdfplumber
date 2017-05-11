from pdfminer.utils import PDFDocEncoding
from decimal import Decimal, ROUND_HALF_UP
import numbers
from operator import itemgetter
import itertools
import six

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
    Adds py3 compatability to pdfminer's version.
    """
    if type(s) == bytes and s.startswith(b'\xfe\xff'):
        return six.text_type(s[2:], 'utf-16be', 'ignore')
    else:
        ords = (ord(c) if type(c) == str else c for c in s)
        return ''.join(PDFDocEncoding[o] for o in ords)

def decimalize(v, q=None):
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
    keep_blank_chars=False
    ):

    x_tolerance = decimalize(x_tolerance)
    y_tolerance = decimalize(y_tolerance)

    def process_word_chars(chars):
        x0, top, x1, bottom = objects_to_bbox(chars)
        return {
            "x0": x0,
            "x1": x1,
            "top": top,
            "bottom": bottom,
            "text": "".join(map(itemgetter("text"), chars))
        }


    def get_line_words(chars, tolerance=DEFAULT_X_TOLERANCE):
        get_text = itemgetter("text")
        chars_sorted = sorted(chars, key=itemgetter("x0"))
        words = []
        current_word = []

        for char in chars_sorted:
            if not keep_blank_chars and get_text(char) == " ":
                if len(current_word) > 0:
                    words.append(current_word)
                    current_word = []
                else: pass
            elif len(current_word) == 0:
                current_word.append(char)
            else:
                last_char = current_word[-1]
                if char["x0"] > (last_char["x1"] + tolerance):
                    words.append(current_word)
                    current_word = []
                current_word.append(char)

        if len(current_word) > 0:
            words.append(current_word)
        processed_words = list(map(process_word_chars, words))
        return processed_words

    chars = to_list(chars)
    doctop_clusters = cluster_objects(chars, "doctop", y_tolerance)

    nested = [ get_line_words(line_chars, tolerance=x_tolerance)
        for line_chars in doctop_clusters ]

    words = list(itertools.chain(*nested))
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

def point_inside_bbox(point, bbox):
    px, py = point
    bx0, by0, bx1, by1 = map(decimalize, bbox)
    return (px >= bx0) and (px <= bx1) and (py >= by0) and (py <= by1)

def obj_inside_bbox_score(obj, bbox):
    corners = (
        (obj["x0"], obj["top"]),
        (obj["x0"], obj["bottom"]),
        (obj["x1"], obj["top"]),
        (obj["x1"], obj["bottom"]),
    )
    score = sum(point_inside_bbox(c, bbox) for c in corners)
    return score

def objects_overlap(a, b):
    bbox = (b["x0"], b["top"], b["x1"], b["bottom"])
    return obj_inside_bbox_score(a, bbox) > 0

def clip_obj(obj, bbox, score=None):
    if score == None:
        score = obj_inside_bbox_score(obj, bbox)
    if score == 0: return None
    if score == 4: return obj
    x0, top, x1, bottom = map(decimalize, bbox)

    copy = dict(obj)
    x_changed = False
    y_changed = False
    if copy["x0"] < x0:
        copy["x0"] = x0
        x_changed = True
    if copy["x1"] > x1:
        copy["x1"] = x1
        x_changed = True
    if copy["top"] < top:
        diff = top - copy["top"]
        copy["top"] = top
        copy["doctop"] = copy["doctop"] + diff
        copy["y1"] = copy["y1"] - diff
        y_changed = True
    if copy["bottom"] > bottom:
        diff = bottom - copy["bottom"]
        copy["bottom"] = bottom
        copy["y0"] = copy["y0"] + diff
        y_changed = True

    if x_changed:
        copy["width"] = copy["x1"] - copy["x0"]
    if y_changed:
        copy["height"] = copy["bottom"] - copy["top"]

    return copy

def n_points_intersecting_bbox(objs, bbox):
    bbox = decimalize(bbox)
    objs = to_list(objs)
    scores = (obj_inside_bbox_score(obj, bbox) for obj in objs)
    return list(scores)


def intersects_bbox(objs, bbox):
    """
    Filters objs to only those intersecting the bbox
    """
    initial_type = type(objs)
    objs = to_list(objs)
    scores = n_points_intersecting_bbox(objs, bbox)
    matching = [ obj for obj, score in zip(objs, scores)
        if score > 0 ]
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
    scores = n_points_intersecting_bbox(objs, bbox)
    matching = [ obj for obj, score in zip(objs, scores)
        if score == 4 ]
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
    scores = n_points_intersecting_bbox(objs, bbox)
    cropped = [ clip_obj(obj, bbox, score)
        for obj, score in zip(objs, scores)
            if score > 0 ]
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
