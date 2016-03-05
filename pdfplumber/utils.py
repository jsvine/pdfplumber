from pdfplumber import helpers
from operator import itemgetter
import itertools
import pandas as pd

def is_dataframe(collection):
    cls = collection.__class__
    name = ".".join([ cls.__module__, cls.__name__ ])
    return name == "pandas.core.frame.DataFrame"

def to_list(collection):
    if is_dataframe(collection):
        return collection.to_dict("records")
    else:
        return collection

def to_dataframe(thing):
    return pd.DataFrame(thing)

def collate_line(line_chars, tolerance=0):
    coll = ""
    last_x1 = None
    for char in sorted(line_chars, key=itemgetter("x0")):
        if last_x1 != None and char["x0"] > (last_x1 + tolerance):
            coll += " "
        last_x1 = char["x1"]
        coll += char["text"]
    return coll

get_0 = itemgetter(0)
get_1 = itemgetter(1)
def collate_chars(chars, x_tolerance=0, y_tolerance=0):
    chars = to_list(chars)
    if len(chars) == 0:
        raise Exception("List of chars is empty.")

    doctops = map(itemgetter("doctop"), chars)

    doctop_clusters = helpers.make_cluster_dict(doctops, y_tolerance)

    with_cluster = ((char, doctop_clusters.get(char["doctop"]))
        for char in chars)

    groups = itertools.groupby(sorted(with_cluster, key=get_1), key=get_1)

    lines = (collate_line(map(get_0, items), x_tolerance)
        for k, items in groups)

    coll = "\n".join(lines)
    return coll

def find_gutters(chars, orientation, min_size=5, include_outer=True):
    if orientation not in ("h", "v"):
        raise ValueError('`orientation` must be "h" or "v".')

    prop = "x0" if orientation == "v" else "top"

    pos = sorted(set(c[prop] for c in chars))

    pos_gaps = ((p1, p2 - p1)
        for p1, p2 in zip(pos, pos[1:]))

    centers = [ g[0] + g[1]/2
        for g in pos_gaps
            if g[1] >= min_size ]

    if include_outer:
        gutters = [ pos[0] ] + centers + [ pos[-1] + 1 ]
    else:
        gutters = centers
    return gutters


def point_inside_bbox(point, bbox):
    px, py = point
    bx0, by0, bx1, by1 = bbox
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
    x0, top, x1, bottom = bbox

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
        copy["doctop"] = copy["doctop"] - diff
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

    using_pandas = isinstance(objs, pd.DataFrame)
    if using_pandas:
        objs = objs.to_dict("records")

    scores = ((obj, obj_inside_bbox_score(obj, bbox)) for obj in objs)

    if crop:
        matching = [ (crop_obj(s[0], bbox, s[1]) if s[1] < 4 else s[0])
            for s in scores if s[1] > 0 ]
    elif strict:
        matching = [ s[0] for s in scores if s[1] == 4 ]
    else:
        matching = [ s[0] for s in scores if s[1] > 0 ]
    
    if using_pandas:
        return pd.DataFrame(matching)
    else:
        return matching

def dividers_to_bounds(dividers):
    return list(zip(dividers, dividers[1:]))

def extract_table(chars,
    v_dividers=None,
    h_dividers=None,
    x_tolerance=0,
    y_tolerance=0):

    using_pandas = isinstance(chars, pd.DataFrame)
    if not using_pandas:
        chars = pd.DataFrame(chars)

    v_bounds = dividers_to_bounds(v_dividers)
    h_bounds = dividers_to_bounds(h_dividers)

    table_arr = []
    for hb in h_bounds:
        row = chars[
            (chars["top"] >= hb[0]) &
            (chars["top"] < hb[1])
        ]
        row_arr = []
        for vb in v_bounds:
            cell = row[
                (row["x0"] >= vb[0]) &
                (row["x0"] < vb[1])
            ]
            if len(cell):
                cell_value = collate_chars(cell, x_tolerance=x_tolerance, y_tolerance=y_tolerance).strip()
            else:
                cell_value = None
            row_arr.append(cell_value)
        table_arr.append(row_arr)

    if using_pandas:
        return pd.DataFrame(table_arr)
    else:
        return table_arr
