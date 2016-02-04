import pandas as pd
import itertools

INF = float("inf")
NEG_INF = float("-inf")

def compatible_iter(thing):
    if hasattr(thing, "iterrows"):
        return thing.iterrows()
    else:
        return enumerate(thing)

def collate_chars(chars, x_tolerance=0, y_tolerance=0):
    using_pandas = isinstance(chars, pd.DataFrame)
    if not using_pandas:
        chars = pd.DataFrame(chars)
    coll = ""
    last_x1 = None
    last_top = None

    if hasattr(chars, "iterrows"):
        iterator = chars.iterrows()
    else:
        iterator = enumerate(chars)

    for i, char in chars.iterrows():
        if last_x1 != None:
            if char["doctop"] > (last_top + y_tolerance):
                coll += "\n"
            if char["x0"] > (last_x1 + x_tolerance):
                coll += " "
        last_x1 = char["x1"]
        last_top = char["doctop"]
        coll += char["text"]

    return coll

def detect_gutters(chars, max_density=0, min_width=5):
    using_pandas = isinstance(chars, pd.DataFrame)
    if not using_pandas:
        chars = pd.DataFrame(chars)
    nonblank = chars[chars["text"].apply(str.strip) != ""]
    x0s = nonblank["x0"].value_counts()
    x1s = nonblank["x1"].value_counts()
    totals = pd.DataFrame({
        "x0": x0s,
        "x1": x1s
    }).sum(axis=1)
    dense_ix = pd.Series(totals[
        totals > max_density
    ].sort_index().index)
    gutters = pd.DataFrame({
        "begin": dense_ix,
        "end": dense_ix.shift(-1)
    })
    gutters["width"] = gutters["end"] - gutters["begin"]
    min_gutters = gutters[
        gutters["width"] >= min_width
    ].reset_index(drop=True)
    if using_pandas:
        return min_gutters
    else:
        return min_gutters.to_dict("records")

def gutters_to_columns(gutters):
    using_pandas = isinstance(gutters, pd.DataFrame)
    if not using_pandas:
        gutters = pd.DataFrame(gutters)
    col_beg = [ None ] + gutters["end"].tolist()
    col_end = gutters["begin"].tolist() + [ None ]
    return list(zip(col_beg, col_end))

def cluster_list(xs, tolerance=0):
    if tolerance == 0: return xs
    if len(xs) < 2: return xs
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

def extract_columns(chars,
    gutter_max_density=0, gutter_min_width=5,
    x_tolerance=0, y_tolerance=0):

    using_pandas = isinstance(chars, pd.DataFrame)
    if not using_pandas:
        chars = pd.DataFrame(chars)

    gutters = detect_gutters(chars,
        min_width=gutter_min_width,
        max_density=gutter_max_density)

    columns = gutters_to_columns(gutters)

    _chars = chars.copy()

    for i, col in enumerate(columns):
        begin, end = col
        _chars.loc[(
            (_chars["x0"] >= (begin or 0)) &
            (_chars["x0"] < (end or (chars["x0"].max() + 1)))
        ), "column"] = i

    collator = lambda x: collate_chars(x, x_tolerance=x_tolerance, y_tolerance=y_tolerance)

    doctop_groups = cluster_list(_chars["doctop"].unique(), y_tolerance)
    doctop_group_dict = dict(itertools.chain(*[
        [ (doctop, i) for doctop in doctops ]
            for i, doctops in enumerate(doctop_groups) ]))

    _chars["doctop_group"] = _chars["doctop"].apply(doctop_group_dict.get)

    collated = _chars.groupby([ "doctop_group", "column" ])\
        .apply(collator)\
        .unstack(level="column")

    if using_pandas:
        return collated
    else:
        return collated.to_dict("records")

def within_bbox(objs, bbox):
    x0, y0, x1, y1 = bbox
    using_pandas = isinstance(objs, pd.DataFrame)
    if not using_pandas:
        objs = pd.DataFrame(objs)
    matching = objs[
        (objs["x0"] >= x0 ) &
        (objs["y0"] >= y0 ) &
        (objs["x0"] < x1 ) &
        (objs["y0"] < y1 )
    ]
    if using_pandas:
        return matching.copy()
    else:
        return matching.to_dict("records")
