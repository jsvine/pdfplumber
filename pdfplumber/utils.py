from pdfminer.utils import PDFDocEncoding
from pdfminer.psparser import PSLiteral
from decimal import Decimal, ROUND_HALF_UP
import numbers
from operator import itemgetter
import itertools
import six

DEFAULT_X_TOLERANCE = 3
DEFAULT_Y_TOLERANCE = 3
DEFAULT_FONTSIZE_TOLERANCE = 0.25 

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

def decode_psl_list(_list):
    return [ decode_text(value.name) if isinstance(value, PSLiteral) else value
        for value in _list ]

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

object_to_bbox = itemgetter("x0", "top", "x1", "bottom")

def objects_to_bbox(objects):
    return (
        min(map(itemgetter("x0"), objects)),
        min(map(itemgetter("top"), objects)),
        max(map(itemgetter("x1"), objects)),
        max(map(itemgetter("bottom"), objects)),
    )

def bbox_to_object(bbox):
    return {
        "x0": bbox[0],
        "top": bbox[1],
        "x1": bbox[2],
        "bottom": bbox[3],
        "width": bbox[2] - bbox[0],
        "height": bbox[3] - bbox[1],
    }

def get_unique_props(objects, prop):
    if len(objects) == 0:
        return None

    props = list(set(map(itemgetter(prop), objects)))

    if len(props) > 1:
        return props
    else:
        return props[0]
        
def extract_words(
        chars,
        x_tolerance = DEFAULT_X_TOLERANCE,
        y_tolerance = DEFAULT_Y_TOLERANCE,
        fontsize_tolerance = DEFAULT_FONTSIZE_TOLERANCE,
        keep_blank_chars = False,
        match_fontsize = True,
        match_fontname = True
    ):

    x_tolerance = decimalize(x_tolerance)
    y_tolerance = decimalize(y_tolerance)
    fontsize_tolerance = decimalize(fontsize_tolerance)

    def process_word_chars(chars):
        x0, top, x1, bottom = objects_to_bbox(chars)

        word = {
            "x0": x0,
            "x1": x1,
            "doctop": min(map(itemgetter("doctop"), chars)),
            "top": top,
            "bottom": bottom,
            "text": "".join(map(itemgetter("text"), chars))
        }

        if match_fontname:
            word["fontname"] = get_unique_props(chars, "fontname")

        if match_fontsize:
            word["fontsize"] = get_unique_props(chars, "size")

        return word


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

    if match_fontsize:
        doctop_clusters = list(itertools.chain.from_iterable(
            cluster_objects(chars, "size", fontsize_tolerance)
              for chars in doctop_clusters))

    if match_fontname:
        doctop_clusters = list(itertools.chain.from_iterable(
            cluster_objects(chars, "fontname", 0)
              for chars in doctop_clusters))

    nested = [ get_line_words(line_chars, tolerance=x_tolerance)
        for line_chars in doctop_clusters ]

    words = sorted(itertools.chain(*nested), key = itemgetter("doctop", "x0"))
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

IS_OUTSIDE = 0
IS_WITHIN = 1
IS_OVERLAPPING = 2

def bboxes_overlap_score(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    outside = \
        (ax1 >= bx2) or \
        (ax2 <= bx1) or \
        (ay1 >= by2) or \
        (ay2 <= by1)
    if outside:
        return IS_OUTSIDE
    else:
        within = \
            (bx1 >= ax1) and \
            (bx2 <= ax2) and \
            (by1 >= ay1) and \
            (by2 <= ay2) 
        if within:
            return IS_WITHIN
        else:
            return IS_OVERLAPPING

def bboxes_overlap(a, b):
    return bboxes_overlap_score(a, b) > 0

def objects_overlap_score(a, b):
    bboxes = tuple(map(object_to_bbox, (a, b)))
    return bboxes_overlap_score(*bboxes)

def objects_overlap(a, b):
    return objects_overlap_score(a, b) > 0

def clip_object(obj, bbox):
    a, b = bbox, object_to_bbox(obj)
    score = bboxes_overlap_score(a, b)
    if score == IS_OUTSIDE:
        # If object is entirely outside the clipping box, reject it
        return None
    elif score == IS_WITHIN:
        # If object is entirely within the bbox, no need to clip it
        return obj

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
        if "doctop" in copy:
            copy["doctop"] = copy["doctop"] + diff
        y_changed = True
    if copy["bottom"] > bottom:
        diff = bottom - copy["bottom"]
        copy["bottom"] = bottom
        y_changed = True

    if x_changed:
        copy["width"] = copy["x1"] - copy["x0"]
    if y_changed:
        copy["height"] = copy["bottom"] - copy["top"]

    return copy

def intersects_bbox(objs, bbox):
    """
    Filters objs to only those intersecting the bbox
    """
    initial_type = type(objs)
    objs = to_list(objs)
    matching = [ obj for obj in objs
        if bboxes_overlap_score(bbox, object_to_bbox(obj)) > 0 ]
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
        if bboxes_overlap_score(bbox, object_to_bbox(obj)) == IS_WITHIN ]
    return initial_type(matching)

def crop_to_bbox(objs, bbox, char_threshold=0.5):
    """
    Filters objs to only those intersecting the bbox,
    and crops the extent of the objects to the bbox.
    """
    if isinstance(objs, dict):
        return dict((k, crop_to_bbox(v, bbox, char_threshold))
            for k,v in objs.items())

    initial_type = type(objs)
    objs = to_list(objs)
    cropped_gen = ((obj, clip_object(obj, bbox)) for obj in objs)

    def test_threshold(orig, cropped):
        if cropped is None:
            ret = False
        elif char_threshold == 0:
            ret = True
        elif orig.get("object_type", "") != "char":
            ret = True
        elif orig['height']*orig['width'] == 0:
            ret = False
        else:
            orig_area = (orig["height"] * orig["width"])
            cropped_area = (cropped["height"] * cropped["width"])
            ratio = cropped_area / orig_area
            ret = ratio >= char_threshold
        return ret

    cropped = [ cropped for orig, cropped in cropped_gen
        if test_threshold(orig, cropped) ]

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
    return obj.__class__(tuple(obj.items()) + tuple(new_items))

def rect_to_edges(rect):
    top, bottom, left, right = [ dict(rect) for x in range(4) ]
    top.update({
        "object_type": "rect_edge",
        "height": decimalize(0),
        "bottom": rect["top"],
        "orientation": "h"
    })
    bottom.update({
        "object_type": "rect_edge",
        "height": decimalize(0),
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
