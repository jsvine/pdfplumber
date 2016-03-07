from pdfplumber import helpers
from pdfminer.utils import PDFDocEncoding
from decimal import Decimal, ROUND_HALF_UP
from operator import itemgetter
import itertools
import six

def decode_text(s):
    """
    Decodes a PDFDocEncoding string to Unicode.
    Adds py3 compatability to pdfminer's version.
    """
    if s.startswith(b'\xfe\xff'):
        return six.text_type(s[2:], 'utf-16be', 'ignore')
    else:
        ords = (ord(c) if type(c) == str else c for c in s)
        return ''.join(PDFDocEncoding[o] for o in ords)

def decimalize(v, q=None):
    if type(v) == int: return Decimal(v)
    if type(v) == float:
        if q != None:
            return Decimal(repr(v)).quantize(Decimal(repr(q)),
                rounding=ROUND_HALF_UP)
        else:
            return Decimal(repr(v))
    return v

def is_dataframe(collection):
    cls = collection.__class__
    name = ".".join([ cls.__module__, cls.__name__ ])
    return name == "pandas.core.frame.DataFrame"

def to_list(collection):
    if is_dataframe(collection):
        return collection.to_dict("records")
    else:
        return collection

def collate_line(line_chars, tolerance=0):
    coll = ""
    last_x1 = None
    for char in sorted(line_chars, key=itemgetter("x0")):
        if last_x1 != None and char["x0"] > (last_x1 + tolerance):
            coll += " "
        last_x1 = char["x1"]
        coll += char["text"]
    return coll

def extract_text(chars, x_tolerance=0, y_tolerance=0):
    if len(chars) == 0:
        raise Exception("List of chars is empty.")

    get_0 = itemgetter(0)
    get_1 = itemgetter(1)

    chars = to_list(chars)

    doctops = map(itemgetter("doctop"), chars)
    doctop_clusters = helpers.make_cluster_dict(doctops, y_tolerance)

    with_cluster = ((char, doctop_clusters.get(char["doctop"]))
        for char in chars)

    groups = itertools.groupby(sorted(with_cluster, key=get_1), key=get_1)
    lines = (collate_line(map(get_0, items), x_tolerance)
        for k, items in groups)

    coll = "\n".join(lines)
    return coll

collate_chars = extract_text

def find_gutters(chars, orientation, min_size=5):
    """
    The size of a gutter is the distance between the beginning
    of the current character and the beginning of the next character.
    """
    if orientation not in ("h", "v"):
        raise ValueError('`orientation` must be "h" or "v".')

    if len(chars) == 0:
        raise ValueError("No chars.")

    start_prop = "x0" if orientation == "v" else "top"
    end_prop = "x1" if orientation == "v" else "bottom"

    get_start = itemgetter(start_prop)
    get_end = itemgetter(end_prop)

    starts = list(sorted(set(map(get_start, chars))))
    end_max = max(map(get_end, chars))

    start_gaps = ((p1, p2 - p1)
        for p1, p2 in zip(starts, starts[1:]))

    gutters = [ g[0] + g[1]/2
        for g in start_gaps
            if g[1] >= min_size ]

    if starts[0] < gutters[0]:
        gutters = [ starts[0] ] + gutters
    if end_max > gutters[-1]:
        gutters = gutters + [ end_max + Decimal('0.001') ]
    return gutters


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

def crop_obj(obj, bbox, score=None):
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

def within_bbox(objs, bbox, strict=True, crop=False):
    """
    strict: Include only objects that are fully within the box?
    crop: Crop lines and rectangles to the box?
    """
    if isinstance(objs, dict):
        return dict((k, within_bbox(v, bbox, strict=strict, crop=crop))
            for k,v in objs.items())

    initial_type = type(objs)
    objs = to_list(objs)

    scores = ((obj, obj_inside_bbox_score(obj, bbox)) for obj in objs)

    if crop:
        matching = [ (crop_obj(s[0], bbox, s[1]) if s[1] < 4 else s[0])
            for s in scores if s[1] > 0 ]
    elif strict:
        matching = [ s[0] for s in scores if s[1] == 4 ]
    else:
        matching = [ s[0] for s in scores if s[1] > 0 ]
    
    return initial_type(matching)

def dividers_to_bounds(dividers):
    return list(zip(dividers, dividers[1:]))

def extract_table(chars, v, h,
    x_tolerance=0,
    y_tolerance=0):

    initial_type = type(chars)
    chars = to_list(chars)

    v_bounds = dividers_to_bounds(v)
    h_bounds = dividers_to_bounds(h)

    table_arr = []
    for hb in h_bounds:
        test = lambda c: (c["top"] >= hb[0]) & (c["top"] < hb[1])
        row = list(filter(test, chars))
        row_arr = []
        for vb in v_bounds:
            test = lambda c: (c["x0"] >= vb[0]) & (c["x0"] < vb[1])
            cell = list(filter(test, row))
            if len(cell):
                cell_value = collate_chars(cell,
                    x_tolerance=x_tolerance,
                    y_tolerance=y_tolerance).strip()
            else:
                cell_value = None
            row_arr.append(cell_value)
        table_arr.append(row_arr)

    return initial_type(table_arr)
