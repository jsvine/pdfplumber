import pandas as pd

INF = float("inf")
NEG_INF = float("-inf")

def compatible_iter(thing):
    if hasattr(thing, "iterrows"):
        return thing.iterrows()
    else:
        return enumerate(thing)

def collate_chars(chars, x_tolerance=0, y_tolerance=0):
    if not isinstance(chars, pd.DataFrame):
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
    if not isinstance(chars, pd.DataFrame):
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
    return gutters[
        gutters["width"] >= min_width
    ].reset_index(drop=True)

def gutters_to_columns(gutter):
    col_beg = [None] + gutter["end"].tolist()
    col_end = gutter["begin"].tolist() + [None]
    return list(zip(col_beg, col_end))

def extract_columns(chars,
    gutter_max_density=0, gutter_min_width=5,
    x_tolerance=0, y_tolerance=0):
    """TKTK
    """
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
    collater = lambda x: collate_chars(x, x_tolerance=x_tolerance, y_tolerance=y_tolerance)
    collated = _chars.groupby([ "doctop", "column" ]).apply(collater)
    return collated.unstack(level="column")
