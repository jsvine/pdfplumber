import itertools
import re
import string
from operator import itemgetter
from typing import Any, Dict, Generator, List, Match, Optional, Pattern, Tuple, Union

from .._typing import T_bbox, T_num, T_obj, T_obj_iter, T_obj_list
from .clustering import cluster_objects
from .generic import to_list
from .geometry import merge_bboxes, obj_to_bbox, objects_to_bbox

DEFAULT_X_TOLERANCE = 3
DEFAULT_Y_TOLERANCE = 3
DEFAULT_X_DENSITY = 7.25
DEFAULT_Y_DENSITY = 13


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
