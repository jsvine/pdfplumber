import itertools
import re
import string
from collections.abc import Sequence
from operator import itemgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    Match,
    Optional,
    Pattern,
    Tuple,
    TypeVar,
    Union,
)

from pdfminer.pdftypes import PDFObjRef
from pdfminer.psparser import PSLiteral
from pdfminer.utils import PDFDocEncoding

from ._typing import T_bbox, T_num, T_obj, T_obj_iter, T_obj_list, T_seq

if TYPE_CHECKING:  # pragma: nocover
    from pandas.core.frame import DataFrame

DEFAULT_X_TOLERANCE = 3
DEFAULT_Y_TOLERANCE = 3
DEFAULT_X_DENSITY = 7.25
DEFAULT_Y_DENSITY = 13


def cluster_list(xs: List[T_num], tolerance: T_num = 0) -> List[List[T_num]]:
    if tolerance == 0:
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


def make_cluster_dict(values: Iterable[T_num], tolerance: T_num) -> Dict[T_num, int]:
    clusters = cluster_list(list(set(values)), tolerance)

    nested_tuples = [
        [(val, i) for val in value_cluster] for i, value_cluster in enumerate(clusters)
    ]

    return dict(itertools.chain(*nested_tuples))


R = TypeVar("R")


def cluster_objects(
    xs: List[R], key_fn: Callable[[R], T_num], tolerance: T_num
) -> List[List[R]]:

    values = map(key_fn, xs)
    cluster_dict = make_cluster_dict(values, tolerance)

    get_0, get_1 = itemgetter(0), itemgetter(1)

    cluster_tuples = sorted(((x, cluster_dict.get(key_fn(x))) for x in xs), key=get_1)

    grouped = itertools.groupby(cluster_tuples, key=get_1)

    return [list(map(get_0, v)) for k, v in grouped]


def decode_text(s: Union[bytes, str]) -> str:
    """
    Decodes a PDFDocEncoding string to Unicode.
    Adds py3 compatibility to pdfminer's version.
    """
    if isinstance(s, bytes) and s.startswith(b"\xfe\xff"):
        return str(s[2:], "utf-16be", "ignore")
    ords = (ord(c) if isinstance(c, str) else c for c in s)
    return "".join(PDFDocEncoding[o] for o in ords)


def resolve_and_decode(obj: Any) -> Any:
    """Recursively resolve the metadata values."""
    if hasattr(obj, "resolve"):
        obj = obj.resolve()
    if isinstance(obj, list):
        return list(map(resolve_and_decode, obj))
    elif isinstance(obj, PSLiteral):
        return decode_text(obj.name)
    elif isinstance(obj, (str, bytes)):
        return decode_text(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = resolve_and_decode(v)
        return obj

    return obj


def decode_psl_list(_list: List[Union[PSLiteral, str]]) -> List[str]:
    return [
        decode_text(value.name) if isinstance(value, PSLiteral) else value
        for value in _list
    ]


def resolve(x: Any) -> Any:
    if isinstance(x, PDFObjRef):
        return x.resolve()
    else:
        return x


def get_dict_type(d: Any) -> Optional[str]:
    if not isinstance(d, dict):
        return None
    t = d.get("Type")
    if isinstance(t, PSLiteral):
        return decode_text(t.name)
    else:
        return t


def resolve_all(x: Any) -> Any:
    """
    Recursively resolves the given object and all the internals.
    """
    if isinstance(x, PDFObjRef):
        resolved = x.resolve()

        # Avoid infinite recursion
        if get_dict_type(resolved) == "Page":
            return x

        return resolve_all(resolved)
    elif isinstance(x, (list, tuple)):
        return type(x)(resolve_all(v) for v in x)
    elif isinstance(x, dict):
        exceptions = ["Parent"] if get_dict_type(x) == "Annot" else []
        return {k: v if k in exceptions else resolve_all(v) for k, v in x.items()}
    else:
        return x


def to_list(collection: Union[T_seq[Any], "DataFrame"]) -> List[Any]:
    if isinstance(collection, list):
        return collection
    elif isinstance(collection, Sequence):
        return list(collection)
    elif hasattr(collection, "to_dict"):
        res: List[Dict[Union[str, int], Any]] = collection.to_dict(
            "records"
        )  # pragma: nocover
        return res
    else:
        return list(collection)


def dedupe_chars(chars: T_obj_list, tolerance: T_num = 1) -> T_obj_list:
    """
    Removes duplicate chars — those sharing the same text, fontname, size,
    and positioning (within `tolerance`) as other characters in the set.
    """
    key = itemgetter("fontname", "size", "upright", "text")
    pos_key = itemgetter("doctop", "x0")

    def yield_unique_chars(chars: T_obj_list) -> Generator[T_obj, None, None]:
        sorted_chars = sorted(chars, key=key)
        for grp, grp_chars in itertools.groupby(sorted_chars, key=key):
            for y_cluster in cluster_objects(
                list(grp_chars), itemgetter("doctop"), tolerance
            ):
                for x_cluster in cluster_objects(
                    y_cluster, itemgetter("x0"), tolerance
                ):
                    yield sorted(x_cluster, key=pos_key)[0]

    deduped = yield_unique_chars(chars)
    return sorted(deduped, key=chars.index)


def objects_to_rect(objects: T_obj_list) -> Dict[str, T_num]:
    return {
        "x0": min(map(itemgetter("x0"), objects)),
        "x1": max(map(itemgetter("x1"), objects)),
        "top": min(map(itemgetter("top"), objects)),
        "bottom": max(map(itemgetter("bottom"), objects)),
    }


def objects_to_bbox(objects: T_obj_list) -> T_bbox:
    return (
        min(map(itemgetter("x0"), objects)),
        min(map(itemgetter("top"), objects)),
        max(map(itemgetter("x1"), objects)),
        max(map(itemgetter("bottom"), objects)),
    )


bbox_getter = itemgetter("x0", "top", "x1", "bottom")


def obj_to_bbox(obj: T_obj) -> T_bbox:
    return bbox_getter(obj)


def bbox_to_rect(bbox: T_bbox) -> Dict[str, T_num]:
    return {"x0": bbox[0], "top": bbox[1], "x1": bbox[2], "bottom": bbox[3]}


def merge_bboxes(bboxes: List[T_bbox]) -> T_bbox:
    """
    Given a set of bounding boxes, return the smallest bounding box that
    contains them all.
    """
    return (
        min(map(itemgetter(0), bboxes)),
        min(map(itemgetter(1), bboxes)),
        max(map(itemgetter(2), bboxes)),
        max(map(itemgetter(3), bboxes)),
    )


class WordExtractor:
    def __init__(
        self,
        x_tolerance: T_num = DEFAULT_X_TOLERANCE,
        y_tolerance: T_num = DEFAULT_Y_TOLERANCE,
        keep_blank_chars: bool = False,
        use_text_flow: bool = False,
        horizontal_ltr: bool = True,  # Should words be read left-to-right?
        vertical_ttb: bool = True,  # Should vertical words be read top-to-bottom?
        extra_attrs: Optional[List[str]] = None,
        split_at_punctuation: Union[bool, str] = False,
    ):
        self.x_tolerance = x_tolerance
        self.y_tolerance = y_tolerance
        self.keep_blank_chars = keep_blank_chars
        self.use_text_flow = use_text_flow
        self.horizontal_ltr = horizontal_ltr
        self.vertical_ttb = vertical_ttb
        self.extra_attrs = [] if extra_attrs is None else extra_attrs

        # Note: string.punctuation = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
        self.split_at_punctuation = (
            string.punctuation
            if split_at_punctuation is True
            else (split_at_punctuation or "")
        )

    def merge_chars(self, ordered_chars: T_obj_list) -> T_obj:
        x0, top, x1, bottom = objects_to_bbox(ordered_chars)
        doctop_adj = ordered_chars[0]["doctop"] - ordered_chars[0]["top"]
        upright = ordered_chars[0]["upright"]

        direction = 1 if (self.horizontal_ltr if upright else self.vertical_ttb) else -1

        word = {
            "text": "".join(map(itemgetter("text"), ordered_chars)),
            "x0": x0,
            "x1": x1,
            "top": top,
            "doctop": top + doctop_adj,
            "bottom": bottom,
            "upright": upright,
            "direction": direction,
        }

        for key in self.extra_attrs:
            word[key] = ordered_chars[0][key]

        return word

    def char_begins_new_word(
        self,
        current_chars: T_obj_list,
        current_bbox: T_bbox,
        next_char: T_obj,
    ) -> bool:

        upright = current_chars[0]["upright"]
        intraline_tol = self.x_tolerance if upright else self.y_tolerance
        interline_tol = self.y_tolerance if upright else self.x_tolerance

        word_x0, word_top, word_x1, word_bottom = current_bbox

        return bool(
            (next_char["x0"] > word_x1 + intraline_tol)
            or (next_char["x1"] < word_x0 - intraline_tol)
            or (next_char["top"] > word_bottom + interline_tol)
            or (next_char["bottom"] < word_top - interline_tol)
        )

    def iter_chars_to_words(
        self, chars: T_obj_iter
    ) -> Generator[T_obj_list, None, None]:
        current_word: T_obj_list = []
        current_bbox: Optional[T_bbox] = None

        def start_next_word(
            new_char: Optional[T_obj],
        ) -> Generator[T_obj_list, None, None]:
            nonlocal current_word
            nonlocal current_bbox

            if current_word:
                yield current_word

            current_word = [] if new_char is None else [new_char]
            current_bbox = None if new_char is None else obj_to_bbox(new_char)

        for char in chars:
            text = char["text"]

            if not self.keep_blank_chars and text.isspace():
                yield from start_next_word(None)

            elif text in self.split_at_punctuation:
                yield from start_next_word(char)
                yield from start_next_word(None)

            elif (
                current_word
                and current_bbox
                and self.char_begins_new_word(current_word, current_bbox, char)
            ):
                yield from start_next_word(char)

            else:
                current_word.append(char)
                if current_bbox is None:
                    current_bbox = obj_to_bbox(char)
                else:
                    current_bbox = merge_bboxes([current_bbox, obj_to_bbox(char)])

        # Finally, after all chars processed
        if current_word:
            yield current_word

    def iter_sort_chars(self, chars: T_obj_iter) -> Generator[T_obj, None, None]:
        def upright_key(x: T_obj) -> int:
            return -int(x["upright"])

        for upright_cluster in cluster_objects(list(chars), upright_key, 0):
            upright = upright_cluster[0]["upright"]
            cluster_key = "doctop" if upright else "x0"

            # Cluster by line
            subclusters = cluster_objects(
                upright_cluster, itemgetter(cluster_key), self.y_tolerance
            )

            for sc in subclusters:
                # Sort within line
                sort_key = "x0" if upright else "doctop"
                to_yield = sorted(sc, key=itemgetter(sort_key))

                # Reverse order if necessary
                if not (self.horizontal_ltr if upright else self.vertical_ttb):
                    yield from reversed(to_yield)
                else:
                    yield from to_yield

    def iter_extract_tuples(
        self, chars: T_obj_iter
    ) -> Generator[Tuple[T_obj, T_obj_list], None, None]:
        if not self.use_text_flow:
            chars = self.iter_sort_chars(chars)

        grouping_key = itemgetter("upright", *self.extra_attrs)
        grouped = itertools.groupby(chars, grouping_key)

        for keyvals, char_group in grouped:
            for word_chars in self.iter_chars_to_words(char_group):
                yield (self.merge_chars(word_chars), word_chars)

    def extract(self, chars: T_obj_list) -> T_obj_list:
        return list(word for word, word_chars in self.iter_extract_tuples(chars))


class LayoutEngine:
    def __init__(
        self,
        x_density: T_num = DEFAULT_X_DENSITY,
        y_density: T_num = DEFAULT_Y_DENSITY,
        x_shift: T_num = 0,
        y_shift: T_num = 0,
        y_tolerance: T_num = DEFAULT_Y_TOLERANCE,
        presorted: bool = False,
    ):
        self.x_density = x_density
        self.y_density = y_density
        self.x_shift = x_shift
        self.y_shift = y_shift
        self.y_tolerance = y_tolerance
        self.presorted = presorted

    def calculate(
        self, word_tuples: List[Tuple[T_obj, T_obj_list]]
    ) -> List[Tuple[str, Optional[T_obj]]]:
        """
        Given a list of (word, chars) tuples, return a list of (char-text,
        char) tuples that can be used to mimic the structural layout of the
        text on the page(s), using the following approach:

        - Sort the words by (doctop, x0) if not already sorted.

        - Calculate the initial doctop for the starting page.

        - Cluster the words by doctop (taking `y_tolerance` into account), and
          iterate through them.

        - For each cluster, calculate the distance between that doctop and the
          initial doctop, in points, minus `y_shift`. Divide that distance by
          `y_density` to calculate the minimum number of newlines that should come
          before this cluster. Append that number of newlines *minus* the number of
          newlines already appended, with a minimum of one.

        - Then for each cluster, iterate through each word in it. Divide each
          word's x0, minus `x_shift`, by `x_density` to calculate the minimum
          number of characters that should come before this cluster.  Append that
          number of spaces *minus* the number of characters and spaces already
          appended, with a minimum of one. Then append the word's text.

        Note: This approach currently works best for horizontal, left-to-right
        text, but will display all words regardless of orientation. There is room
        for improvement in better supporting right-to-left text, as well as
        vertical text.
        """
        rendered: List[Tuple[str, Optional[T_obj]]] = []

        if not len(word_tuples):
            return rendered

        num_newlines = 0
        words_sorted = (
            word_tuples
            if self.presorted
            else sorted(word_tuples, key=lambda x: (x[0]["doctop"], x[0]["x0"]))
        )
        first_word = words_sorted[0][0]
        doctop_start = first_word["doctop"] - first_word["top"]
        for ws in cluster_objects(
            words_sorted, lambda x: float(x[0]["doctop"]), self.y_tolerance
        ):
            y_dist = (
                ws[0][0]["doctop"] - (doctop_start + self.y_shift)
            ) / self.y_density
            num_newlines_prepend = max(
                min(1, num_newlines), round(y_dist) - num_newlines
            )
            rendered += [("\n", None)] * num_newlines_prepend
            num_newlines += num_newlines_prepend

            line_len = 0
            for word, chars in sorted(ws, key=lambda x: float(x[0]["x0"])):
                x_dist = (word["x0"] - self.x_shift) / self.x_density
                num_spaces_prepend = max(min(1, line_len), round(x_dist) - line_len)
                rendered += [(" ", None)] * num_spaces_prepend
                for c in chars:
                    for letter in c["text"]:
                        rendered.append((letter, c))
                line_len += num_spaces_prepend + len(word["text"])
        return rendered


def extract_words(
    chars: T_obj_list,
    x_tolerance: T_num = DEFAULT_X_TOLERANCE,
    y_tolerance: T_num = DEFAULT_Y_TOLERANCE,
    keep_blank_chars: bool = False,
    use_text_flow: bool = False,
    horizontal_ltr: bool = True,  # Should words be read left-to-right?
    vertical_ttb: bool = True,  # Should vertical words be read top-to-bottom?
    extra_attrs: Optional[List[str]] = None,
    split_at_punctuation: Union[bool, str] = False,
) -> T_obj_list:
    return WordExtractor(
        x_tolerance=x_tolerance,
        y_tolerance=y_tolerance,
        keep_blank_chars=keep_blank_chars,
        use_text_flow=use_text_flow,
        horizontal_ltr=horizontal_ltr,
        vertical_ttb=vertical_ttb,
        extra_attrs=extra_attrs,
        split_at_punctuation=split_at_punctuation,
    ).extract(chars)


class TextLayout:
    def __init__(
        self, chars: T_obj_list, extractor: WordExtractor, engine: LayoutEngine
    ):
        self.chars = chars
        self.extractor = extractor
        self.engine = engine
        self.word_tuples = list(extractor.iter_extract_tuples(chars))
        self.layout_tuples = engine.calculate(self.word_tuples)
        self.as_string = "".join(map(itemgetter(0), self.layout_tuples))

    def to_string(self) -> str:
        return self.as_string

    def search(
        self, pattern: Union[str, Pattern[str]], regex: bool = True, case: bool = True
    ) -> List[Dict[str, Any]]:
        def match_to_dict(m: Match[str]) -> Dict[str, Any]:
            subset = self.layout_tuples[m.start() : m.end()]
            chars = [c for (text, c) in subset if c is not None]
            x0, top, x1, bottom = objects_to_bbox(chars)
            return {
                "text": m.group(0),
                "groups": m.groups(),
                "x0": x0,
                "top": top,
                "x1": x1,
                "bottom": bottom,
                "chars": chars,
            }

        if isinstance(pattern, Pattern):
            if regex is False:
                raise ValueError(
                    "Cannot pass a compiled search pattern *and* regex=False together."
                )
            if case is False:
                raise ValueError(
                    "Cannot pass a compiled search pattern *and* case=False together."
                )
            compiled = pattern
        else:
            if regex is False:
                pattern = re.escape(pattern)

            flags = re.I if case is False else 0
            compiled = re.compile(pattern, flags)

        gen = re.finditer(compiled, self.as_string)
        return list(map(match_to_dict, gen))


def collate_line(
    line_chars: T_obj_list, tolerance: T_num = DEFAULT_X_TOLERANCE, layout: bool = False
) -> str:
    coll = ""
    last_x1 = None
    for char in sorted(line_chars, key=itemgetter("x0")):
        if (last_x1 is not None) and (char["x0"] > (last_x1 + tolerance)):
            coll += " "
        last_x1 = char["x1"]
        coll += char["text"]
    return coll


def chars_to_layout(
    chars: T_obj_list,
    x_density: T_num = DEFAULT_X_DENSITY,
    y_density: T_num = DEFAULT_Y_DENSITY,
    x_shift: T_num = 0,
    y_shift: T_num = 0,
    x_tolerance: T_num = DEFAULT_X_TOLERANCE,
    y_tolerance: T_num = DEFAULT_Y_TOLERANCE,
    keep_blank_chars: bool = False,
    use_text_flow: bool = False,
    horizontal_ltr: bool = True,  # Should words be read left-to-right?
    vertical_ttb: bool = True,  # Should vertical words be read top-to-bottom?
    extra_attrs: Optional[List[str]] = None,
    split_at_punctuation: Union[bool, str] = False,
) -> TextLayout:
    extractor = WordExtractor(
        x_tolerance=x_tolerance,
        y_tolerance=y_tolerance,
        keep_blank_chars=keep_blank_chars,
        use_text_flow=use_text_flow,
        horizontal_ltr=horizontal_ltr,
        vertical_ttb=vertical_ttb,
        extra_attrs=extra_attrs,
        split_at_punctuation=split_at_punctuation,
    )

    engine = LayoutEngine(
        x_density=x_density,
        y_density=y_density,
        x_shift=x_shift,
        y_shift=y_shift,
        y_tolerance=y_tolerance,
        presorted=True,
    )

    return TextLayout(chars, extractor, engine)


def extract_text(
    chars: T_obj_list,
    layout: bool = False,
    x_density: T_num = DEFAULT_X_DENSITY,
    y_density: T_num = DEFAULT_Y_DENSITY,
    x_shift: T_num = 0,
    y_shift: T_num = 0,
    x_tolerance: T_num = DEFAULT_X_TOLERANCE,
    y_tolerance: T_num = DEFAULT_Y_TOLERANCE,
    keep_blank_chars: bool = False,
    use_text_flow: bool = False,
    horizontal_ltr: bool = True,  # Should words be read left-to-right?
    vertical_ttb: bool = True,  # Should vertical words be read top-to-bottom?
    extra_attrs: Optional[List[str]] = None,
    split_at_punctuation: Union[bool, str] = False,
) -> str:
    chars = to_list(chars)
    if len(chars) == 0:
        return ""

    if layout:
        calculated_layout = chars_to_layout(
            chars,
            x_tolerance=x_tolerance,
            y_tolerance=y_tolerance,
            keep_blank_chars=keep_blank_chars,
            use_text_flow=use_text_flow,
            horizontal_ltr=horizontal_ltr,
            vertical_ttb=vertical_ttb,
            extra_attrs=extra_attrs,
            split_at_punctuation=split_at_punctuation,
            x_density=x_density,
            y_density=y_density,
            x_shift=x_shift,
            y_shift=y_shift,
        )
        return calculated_layout.to_string()

    else:
        doctop_clusters = cluster_objects(chars, itemgetter("doctop"), y_tolerance)

        lines = (
            collate_line(line_chars, x_tolerance) for line_chars in doctop_clusters
        )

        return "\n".join(lines)


def get_bbox_overlap(a: T_bbox, b: T_bbox) -> Optional[T_bbox]:
    a_left, a_top, a_right, a_bottom = a
    b_left, b_top, b_right, b_bottom = b
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


def calculate_area(bbox: T_bbox) -> T_num:
    left, top, right, bottom = bbox
    if left > right or top > bottom:
        raise ValueError(f"{bbox} has a negative width or height.")
    return (right - left) * (bottom - top)


def clip_obj(obj: T_obj, bbox: T_bbox) -> Optional[T_obj]:

    overlap = get_bbox_overlap(obj_to_bbox(obj), bbox)
    if overlap is None:
        return None

    dims = bbox_to_rect(overlap)
    copy = dict(obj)

    for attr in ["x0", "top", "x1", "bottom"]:
        copy[attr] = dims[attr]

    diff = dims["top"] - obj["top"]
    copy["doctop"] = obj["doctop"] + diff
    copy["width"] = copy["x1"] - copy["x0"]
    copy["height"] = copy["bottom"] - copy["top"]

    return copy


def intersects_bbox(objs: T_obj_list, bbox: T_bbox) -> T_obj_list:
    """
    Filters objs to only those intersecting the bbox
    """
    initial_type = type(objs)
    objs = to_list(objs)
    matching = [
        obj for obj in objs if get_bbox_overlap(obj_to_bbox(obj), bbox) is not None
    ]
    return initial_type(matching)


def within_bbox(objs: T_obj_list, bbox: T_bbox) -> T_obj_list:
    """
    Filters objs to only those fully within the bbox
    """
    return [
        obj
        for obj in objs
        if get_bbox_overlap(obj_to_bbox(obj), bbox) == obj_to_bbox(obj)
    ]


def outside_bbox(objs: T_obj_list, bbox: T_bbox) -> T_obj_list:
    """
    Filters objs to only those fully outside the bbox
    """
    return [obj for obj in objs if get_bbox_overlap(obj_to_bbox(obj), bbox) is None]


def crop_to_bbox(objs: T_obj_list, bbox: T_bbox) -> T_obj_list:
    """
    Filters objs to only those intersecting the bbox,
    and crops the extent of the objects to the bbox.
    """
    return list(filter(None, (clip_obj(obj, bbox) for obj in objs)))


def move_object(obj: T_obj, axis: str, value: T_num) -> T_obj:
    assert axis in ("h", "v")
    if axis == "h":
        new_items = [
            ("x0", obj["x0"] + value),
            ("x1", obj["x1"] + value),
        ]
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


def snap_objects(objs: T_obj_list, attr: str, tolerance: T_num) -> T_obj_list:
    axis = {"x0": "h", "x1": "h", "top": "v", "bottom": "v"}[attr]
    clusters = cluster_objects(objs, itemgetter(attr), tolerance)
    avgs = [sum(map(itemgetter(attr), objs)) / len(objs) for objs in clusters]
    snapped_clusters = [
        [move_object(obj, axis, avg - obj[attr]) for obj in cluster]
        for cluster, avg in zip(clusters, avgs)
    ]
    return list(itertools.chain(*snapped_clusters))


def resize_object(obj: T_obj, key: str, value: T_num) -> T_obj:
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


def curve_to_edges(curve: T_obj) -> T_obj_list:
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


def rect_to_edges(rect: T_obj) -> T_obj_list:
    top, bottom, left, right = [dict(rect) for x in range(4)]
    top.update(
        {
            "object_type": "rect_edge",
            "height": 0,
            "y0": rect["y1"],
            "bottom": rect["top"],
            "orientation": "h",
        }
    )
    bottom.update(
        {
            "object_type": "rect_edge",
            "height": 0,
            "y1": rect["y0"],
            "top": rect["top"] + rect["height"],
            "doctop": rect["doctop"] + rect["height"],
            "orientation": "h",
        }
    )
    left.update(
        {
            "object_type": "rect_edge",
            "width": 0,
            "x1": rect["x0"],
            "orientation": "v",
        }
    )
    right.update(
        {
            "object_type": "rect_edge",
            "width": 0,
            "x0": rect["x1"],
            "orientation": "v",
        }
    )
    return [top, bottom, left, right]


def line_to_edge(line: T_obj) -> T_obj:
    edge = dict(line)
    edge["orientation"] = "h" if (line["top"] == line["bottom"]) else "v"
    return edge


def obj_to_edges(obj: T_obj) -> T_obj_list:
    return {
        "line": lambda x: [line_to_edge(x)],
        "rect": rect_to_edges,
        "rect_edge": rect_to_edges,
        "curve": curve_to_edges,
    }[obj["object_type"]](obj)


def filter_edges(
    edges: T_obj_list,
    orientation: Optional[str] = None,
    edge_type: Optional[str] = None,
    min_length: T_num = 1,
) -> T_obj_list:

    if orientation not in ("v", "h", None):
        raise ValueError("Orientation must be 'v' or 'h'")

    def test(e: T_obj) -> bool:
        dim = "height" if e["orientation"] == "v" else "width"
        et_correct = e["object_type"] == edge_type if edge_type is not None else True
        orient_correct = orientation is None or e["orientation"] == orientation
        return bool(et_correct and orient_correct and (e[dim] >= min_length))

    return list(filter(test, edges))
