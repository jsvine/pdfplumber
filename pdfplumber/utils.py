import pandas as pd
import itertools

def compatible_iter(thing):
    if hasattr(thing, "iterrows"):
        return thing.iterrows()
    else:
        return enumerate(thing)

def cluster_list(xs, tolerance=0):
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
    clusters = cluster_list(set(values), tolerance)

    nested_tuples = [ [ (val, i) for val in value_cluster ]
        for i, value_cluster in enumerate(clusters) ]

    cluster_dict = dict(itertools.chain(*nested_tuples))
    return cluster_dict 

def collate_chars(chars, x_tolerance=0, y_tolerance=0):
    using_pandas = isinstance(chars, pd.DataFrame)
    if using_pandas:
        _chars = chars.copy()
    else:
        _chars = pd.DataFrame(chars)

    def collate_line(line_chars):
        coll = ""
        last_x1 = None
        for i, char in line_chars.sort_values("x0").iterrows():
            if last_x1 != None and char["x0"] > (last_x1 + x_tolerance):
                coll += " "
            last_x1 = char["x1"]
            coll += char["text"]
        return coll

    doctop_clusters = make_cluster_dict(_chars["doctop"], y_tolerance)
    _chars["doctop_cluster"] = _chars["doctop"].apply(doctop_clusters.get)
    dc_grp = _chars.sort_values("doctop_cluster").groupby("doctop_cluster")
    coll = "\n".join(dc_grp.apply(collate_line))
    return coll

def detect_gutters(chars, min_width=5):
    using_pandas = isinstance(chars, pd.DataFrame)
    if not using_pandas:
        chars = pd.DataFrame(chars)
    nonblank = chars[chars["text"].str.strip() != ""]
    x0s = nonblank["x0"].value_counts()
    x1s = nonblank["x1"].value_counts()
    totals = pd.DataFrame({
        "x0": x0s,
        "x1": x1s
    }).sum(axis=1)
    dense_ix = pd.Series(totals[
        totals > 0
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

def extract_columns(chars,
    x_tolerance=0, y_tolerance=0,
    gutter_min_width=5):

    using_pandas = isinstance(chars, pd.DataFrame)
    if not using_pandas:
        chars = pd.DataFrame(chars)

    gutters = detect_gutters(chars, min_width=gutter_min_width)

    columns = gutters_to_columns(gutters)

    _chars = chars.copy()

    for i, col in enumerate(columns):
        begin, end = col
        _chars.loc[(
            (_chars["x0"] >= (begin or 0)) &
            (_chars["x0"] < (end or (chars["x0"].max() + 1)))
        ), "column"] = i

    collator = lambda x: collate_chars(x, x_tolerance=x_tolerance, y_tolerance=y_tolerance)

    doctop_clusters = make_cluster_dict(_chars["doctop"], y_tolerance)
    _chars["doctop_cluster"] = _chars["doctop"].apply(doctop_clusters.get)

    collated = _chars.groupby([ "doctop_cluster", "column" ])\
        .apply(collator)\
        .unstack(level="column")

    collated.columns = list(map(int, collated.columns))

    if using_pandas:
        return collated
    else:
        return collated.fillna("").to_dict("records")

def within_bbox(objs, bbox):
    x0, top0, x1, top1 = bbox
    using_pandas = isinstance(objs, pd.DataFrame)
    if not using_pandas:
        objs = pd.DataFrame(objs)
    matching = objs[
        (objs["x0"] >= x0 ) &
        (objs["top"] >= top0 ) &
        (objs["x0"] < x1 ) &
        (objs["top"] < top1 )
    ]
    if using_pandas:
        return matching.copy()
    else:
        return matching.to_dict("records")
