import re
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Pattern,
    Tuple,
    Union,
)
from unicodedata import normalize as normalize_unicode
from warnings import warn

from paves.miner import (
    LTChar,
    LTComponent,
    LTContainer,
    LTCurve,
    LTItem,
    LTPage,
    LTTextContainer,
    MarkedContent,
    PDFPage,
    extract_page,
)
from playa.color import Color
from playa.page import ContentObject, GlyphObject, ImageObject, PathObject, PathSegment
from playa.utils import mult_matrix, translate_matrix

from . import utils
from ._typing import T_bbox, T_num, T_obj, T_obj_list
from .container import Container
from .structure import PDFStructTree, StructTreeMissing
from .table import T_table_settings, Table, TableFinder, TableSettings
from .utils import resolve_all, resolve_and_decode
from .utils.text import TextMap

lt_pat = re.compile(r"^LT")

ALL_ATTRS = set(
    [
        "adv",
        "height",
        "linewidth",
        "pts",
        "size",
        "srcsize",
        "width",
        "x0",
        "x1",
        "y0",
        "y1",
        "bits",
        "matrix",
        "upright",
        "fontname",
        "text",
        "render_mode",
        "imagemask",
        "colorspace",
        "evenodd",
        "fill",
        "non_stroking_color",
        "stroke",
        "stroking_color",
        "stream",
        "name",
        "mcid",
        "tag",
    ]
)


if TYPE_CHECKING:  # pragma: nocover
    from .display import PageImage
    from .pdf import PDF

# via https://git.ghostscript.com/?p=mupdf.git;a=blob;f=source/pdf/pdf-font.c;h=6322cedf2c26cfb312c0c0878d7aff97b4c7470e;hb=HEAD#l774   # noqa

CP936_FONTNAMES = {
    b"\xcb\xce\xcc\xe5": "SimSun,Regular",
    b"\xba\xda\xcc\xe5": "SimHei,Regular",
    b"\xbf\xac\xcc\xe5_GB2312": "SimKai,Regular",
    b"\xb7\xc2\xcb\xce_GB2312": "SimFang,Regular",
    b"\xc1\xa5\xca\xe9": "SimLi,Regular",
}


def fix_fontname_bytes(fontname: bytes) -> str:
    if b"+" in fontname:
        split_at = fontname.index(b"+") + 1
        prefix, suffix = fontname[:split_at], fontname[split_at:]
    else:
        prefix, suffix = b"", fontname

    suffix_new = CP936_FONTNAMES.get(suffix, str(suffix)[2:-1])
    return str(prefix)[2:-1] + suffix_new


def separate_pattern(
    color: Color,
) -> Tuple[Optional[Tuple[Union[float, int], ...]], Optional[str]]:
    return color.values, color.pattern


def normalize_color(
    color: Union[Color, None],
) -> Tuple[Optional[Tuple[Union[float, int], ...]], Optional[str]]:
    if color is None:
        return (None, None)
    return separate_pattern(color)


def tuplify_list_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: (tuple(value) if isinstance(value, list) else value)
        for key, value in kwargs.items()
    }


def _normalize_box(box_raw: T_bbox, rotation: T_num = 0) -> T_bbox:
    # Per PDF Reference 3.8.4: "Note: Although rectangles are
    # conventionally specified by their lower-left and upperright
    # corners, it is acceptable to specify any two diagonally opposite
    # corners."
    x0, x1 = sorted((box_raw[0], box_raw[2]))
    y0, y1 = sorted((box_raw[1], box_raw[3]))
    if rotation in [90, 270]:
        return (y0, x0, y1, x1)
    else:
        return (x0, y0, x1, y1)


# PDFs coordinate spaces refer to an origin in the bottom-left of the
# page; pdfplumber flips this vertically, so that the origin is in the
# top-left.
def _invert_box(box_raw: T_bbox, mb_height: T_num) -> T_bbox:
    x0, y0, x1, y1 = box_raw
    return (x0, mb_height - y1, x1, mb_height - y0)


def flatten_contents(objs: Union[PDFPage, ContentObject]) -> Iterator[ContentObject]:
    """Traverse a PDF page, recursing into text, path, and xobjects."""
    if isinstance(objs, PathObject):
        # PathObjects are a bit special since they always contain at
        # least one subpath, and these are a flat list (do not recurse)
        yield from objs
    else:
        # Other ContentObjects are iterable and possibly multiply
        # nested (in the case of XObjects), but only some of them
        # actually contain other objects.  We *could* check the length
        # of an object first but this is wasteful, so we don't.
        count = 0
        for obj in objs:
            yield from flatten_contents(obj)
            count += 1
        if count == 0 and not isinstance(objs, PDFPage):
            yield objs


def is_closed(segs: List[PathSegment]) -> bool:
    """Detect a closed shape."""
    if segs[-1].operator == "h":  # Easy, it tells us it's closed!
        return True
    if segs[-1].points[-1] == segs[0].points[-1]:
        return True
    return False


def is_rectangular(segs: List[PathSegment]) -> bool:
    """Detect a rectangular shape.

    TODO: Rectangular here is defined in device space, what about
    rotated rectangles?  Are they not rectangles too?  If you prick
    yourself on them, do you not bleed?
    """
    # A rectangle has four sides (exception for a redundant 'h')
    if len(segs) > 5 or (len(segs) == 5 and segs[4].operator != "h"):
        return False
    xs = []
    ys = []
    # TODO: This could be done with fancy list comprehensions which
    # might be slightly faster but much less easy to understand.
    for seg in segs[:4]:
        if seg.operator == "h":
            x, y = segs[0].points[-1]
        else:
            x, y = seg.points[-1]
        xs.append(x)
        ys.append(y)
    if xs[0] == xs[1] and ys[1] == ys[2] and xs[2] == xs[3] and ys[3] == ys[0]:
        return True
    if ys[0] == ys[1] and xs[1] == xs[2] and ys[2] == ys[3] and xs[3] == xs[0]:
        return True
    return False


class Page(Container):
    cached_properties: List[str] = Container.cached_properties + ["_layout"]
    is_original: bool = True
    pages = None

    def __init__(
        self,
        pdf: "PDF",
        page_obj: PDFPage,
        page_number: int,
        initial_doctop: T_num = 0,
    ):
        self.pdf = pdf
        self.root_page = self
        self.page_obj = page_obj
        self.page_number = page_number
        self.initial_doctop = initial_doctop

        def get_attr(key: str, default: Any = None) -> Any:
            value = resolve_all(page_obj.attrs.get(key))
            return default if value is None else value

        # Per PDF Reference Table 3.27: "The number of degrees by which the
        # page should be rotated clockwise when displayed or printed. The value
        # must be a multiple of 90. Default value: 0"
        _rotation = get_attr("Rotate", 0)
        self.rotation = _rotation % 360

        mb_raw = _normalize_box(get_attr("MediaBox"), self.rotation)
        mb_height = mb_raw[3] - mb_raw[1]

        self.mediabox = _invert_box(mb_raw, mb_height)

        if "CropBox" in page_obj.attrs:
            self.cropbox = _invert_box(
                _normalize_box(get_attr("CropBox"), self.rotation), mb_height
            )
        else:
            self.cropbox = self.mediabox

        # Page.bbox defaults to self.mediabox, but can be altered by Page.crop(...)
        self.bbox = self.mediabox

        # See https://rednafi.com/python/lru_cache_on_methods/
        self.get_textmap = lru_cache()(self._get_textmap)

    def close(self) -> None:
        self.flush_cache()
        self.get_textmap.cache_clear()

    @property
    def width(self) -> T_num:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> T_num:
        return self.bbox[3] - self.bbox[1]

    @property
    def structure_tree(self) -> List[Dict[str, Any]]:
        """Return the structure tree for a page, if any."""
        try:
            return [elem.to_dict() for elem in PDFStructTree(self.pdf, self)]
        except StructTreeMissing:
            return []

    @property
    def layout(self) -> LTPage:
        if hasattr(self, "_layout"):
            return self._layout
        self._layout: LTPage = extract_page(self.page_obj, self.pdf.laparams)
        return self._layout

    @property
    def annots(self) -> T_obj_list:
        def rotate_point(pt: Tuple[float, float], r: int) -> Tuple[float, float]:
            turns = r // 90
            for i in range(turns):
                x, y = pt
                comp = self.width if i == turns % 2 else self.height
                pt = (y, (comp - x))
            return pt

        def parse(annot: T_obj) -> T_obj:
            _a, _b, _c, _d = annot["Rect"]
            pt0 = rotate_point((_a, _b), self.rotation)
            pt1 = rotate_point((_c, _d), self.rotation)
            rh = self.root_page.height
            x0, top, x1, bottom = _invert_box(_normalize_box((*pt0, *pt1)), rh)

            a = annot.get("A", {})
            extras = {
                "uri": a.get("URI"),
                "title": annot.get("T"),
                "contents": annot.get("Contents"),
            }
            for k, v in extras.items():
                if v is not None:
                    try:
                        extras[k] = v.decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                            extras[k] = v.decode("utf-16")
                        except UnicodeDecodeError:
                            if self.pdf.raise_unicode_errors:
                                raise
                            warn(
                                f"Could not decode {k} of annotation."
                                f" {k} will be missing."
                            )

            parsed = {
                "page_number": self.page_number,
                "object_type": "annot",
                "x0": x0,
                "y0": rh - bottom,
                "x1": x1,
                "y1": rh - top,
                "doctop": self.initial_doctop + top,
                "top": top,
                "bottom": bottom,
                "width": x1 - x0,
                "height": bottom - top,
            }
            parsed.update(extras)
            # Replace the indirect reference to the page dictionary
            # with a pointer to our actual page
            if "P" in annot:
                annot["P"] = self
            parsed["data"] = annot
            return parsed

        raw = resolve_all(self.page_obj.annots) or []
        parsed = list(map(parse, raw))
        if isinstance(self, CroppedPage):
            return self._crop_fn(parsed)
        else:
            return parsed

    @property
    def hyperlinks(self) -> T_obj_list:
        return [a for a in self.annots if a["uri"] is not None]

    @property
    def objects(self) -> Dict[str, T_obj_list]:
        if hasattr(self, "_objects"):
            return self._objects
        self._objects: Dict[str, T_obj_list] = self.parse_objects()
        return self._objects

    def point2coord(self, pt: Tuple[T_num, T_num]) -> Tuple[T_num, T_num]:
        # See note below re. #1181 and mediabox-adjustment reversions
        return (self.mediabox[0] + pt[0], self.mediabox[1] + self.height - pt[1])

    def process_object(self, obj: LTItem) -> T_obj:
        kind = re.sub(lt_pat, "", obj.__class__.__name__).lower()

        def process_attr(item: Tuple[str, Any]) -> Optional[Tuple[str, Any]]:
            k, v = item
            if k in ALL_ATTRS:
                res = resolve_all(v)
                return (k, res)
            else:
                return None

        attr = dict(filter(None, map(process_attr, obj.__dict__.items())))

        attr["object_type"] = kind
        attr["page_number"] = self.page_number

        # Find the first enclosing marked content section
        mcs: Union[MarkedContent, None] = None
        if hasattr(obj, "mcstack"):  # LTAnno does not
            for mcs in reversed(obj.mcstack):
                if mcs is not None and mcs.mcid is not None:
                    break
        if mcs is not None:
            attr["mcid"] = mcs.mcid
            attr["tag"] = mcs.tag

        for cs in ["ncs", "scs"]:
            # PAVÈS does expose these attributes unlike pdfminer.six
            if hasattr(obj, cs):
                attr[cs] = resolve_and_decode(getattr(obj, cs).name)

        for color_attr, pattern_attr in [
            ("stroking_color", "stroking_pattern"),
            ("non_stroking_color", "non_stroking_pattern"),
        ]:
            if color_attr in attr:
                attr[color_attr], attr[pattern_attr] = normalize_color(attr[color_attr])

        if isinstance(obj, (LTChar, LTTextContainer)):
            text = obj.get_text()
            attr["text"] = (
                normalize_unicode(self.pdf.unicode_norm, text)
                if self.pdf.unicode_norm is not None
                else text
            )

        if isinstance(obj, LTChar):
            # pdfminer.six (at least as of v20221105) does not
            # directly expose .stroking_color and .non_stroking_color
            # for LTChar objects (unlike, e.g., LTRect objects).
            gs = obj.graphicstate
            attr["stroking_color"], attr["stroking_pattern"] = normalize_color(
                gs.scolor
            )
            attr["non_stroking_color"], attr["non_stroking_pattern"] = normalize_color(
                gs.ncolor
            )

            # Handle (rare) byte-encoded fontnames
            if isinstance(attr["fontname"], bytes):
                attr["fontname"] = fix_fontname_bytes(attr["fontname"])

        elif isinstance(obj, (LTCurve,)):
            attr["pts"] = list(map(self.point2coord, attr["pts"]))
            # Ignoring typing because type signature for obj.original_path
            # appears to be incorrect (PAVÉS is bug compatible here, oops)
            attr["path"] = [
                (cmd, *map(self.point2coord, pts))  # type: ignore
                for cmd, *pts in obj.original_path
            ]
            attr["dash"] = obj.dashing_style

        # As noted in #1181, `pdfminer.six` adjusts objects'
        # coordinates relative to the MediaBox:
        # https://github.com/pdfminer/pdfminer.six/blob/1a8bd2f730295b31d6165e4d95fcb5a03793c978/pdfminer/converter.py#L79-L84
        # (PAVÉS does this too, because it is not wrong)
        mb_x0, mb_top = self.mediabox[:2]

        if "y0" in attr:
            attr["top"] = (self.height - attr["y1"]) + mb_top
            attr["bottom"] = (self.height - attr["y0"]) + mb_top
            attr["doctop"] = self.initial_doctop + attr["top"]

        if "x0" in attr and mb_x0 != 0:
            attr["x0"] = attr["x0"] + mb_x0
            attr["x1"] = attr["x1"] + mb_x0

        return attr

    def iter_layout_objects(
        self, layout_objects: List[LTComponent]
    ) -> Generator[T_obj, None, None]:
        for obj in layout_objects:
            # If object is, like LTFigure, a higher-level object ...
            if isinstance(obj, LTContainer):
                # and LAParams is passed, process the object itself.
                if self.pdf.laparams is not None:
                    yield self.process_object(obj)
                # Regardless, iterate through its children
                yield from self.iter_layout_objects(obj._objs)
            else:
                yield self.process_object(obj)

    def parse_objects(self) -> Dict[str, T_obj_list]:
        objects: Dict[str, T_obj_list] = {}
        if self.pdf.laparams is None:
            return self.parse_playa_objects()
        for obj in self.iter_layout_objects(self.layout._objs):
            kind = obj["object_type"]
            if kind in ["anno"]:
                continue
            if objects.get(kind) is None:
                objects[kind] = []
            objects[kind].append(obj)
        return objects

    def process_playa_object(self, content_object: ContentObject) -> T_obj:
        kind = content_object.object_type
        obj: T_obj = {"object_type": kind, "page_number": self.page_number}

        if content_object.mcs is not None:
            obj["mcid"] = content_object.mcs.mcid
            obj["tag"] = content_object.mcs.tag

        gstate = content_object.gstate
        # These cannot be None, but they might be the defaults
        obj["ncs"] = resolve_and_decode(gstate.ncs.name)
        obj["scs"] = resolve_and_decode(gstate.scs.name)
        obj["stroking_color"] = gstate.scolor.values
        obj["stroking_pattern"] = gstate.scolor.pattern
        obj["non_stroking_color"] = gstate.ncolor.values
        obj["non_stroking_pattern"] = gstate.ncolor.pattern
        obj["linewidth"] = gstate.linewidth

        # As noted in #1181, `pdfminer.six` (and `playa` by default) adjust objects'
        # coordinates relative to the MediaBox:
        # https://github.com/pdfminer/pdfminer.six/blob/1a8bd2f730295b31d6165e4d95fcb5a03793c978/pdfminer/converter.py#L79-L84
        mb_x0, mb_top = self.mediabox[:2]

        try:
            x0, y0, x1, y1 = content_object.bbox
            obj["x0"] = x0 + mb_x0
            obj["x1"] = x1 + mb_x0
            obj["y0"] = y0  # FIXME: but... what about the MediaBox?
            obj["y1"] = y1
            obj["top"] = (self.height - y1) + mb_top
            obj["bottom"] = (self.height - y0) + mb_top
            obj["doctop"] = self.initial_doctop + obj["top"]
            obj["height"] = abs(y1 - y0)
            obj["width"] = abs(x1 - x0)
        except ValueError:
            # It's an object with no bbox (e.g. a marked content point)
            pass

        if isinstance(content_object, GlyphObject):
            text = content_object.text
            obj["object_type"] = "char"
            obj["adv"] = content_object.adv
            textstate = content_object.textstate
            obj["text"] = (
                normalize_unicode(self.pdf.unicode_norm, text)
                if text and self.pdf.unicode_norm is not None
                else text
            )
            obj["render_mode"] = textstate.render_mode
            # Lazy API does not do this stuff for you
            if textstate.font is not None:
                obj["fontname"] = textstate.font.fontname
                if textstate.font.vertical:
                    obj["size"] = textstate.fontsize * content_object.matrix[0]
                else:
                    obj["size"] = textstate.fontsize * content_object.matrix[3]
            matrix = mult_matrix(textstate.line_matrix, content_object.ctm)
            matrix = translate_matrix(matrix, textstate.glyph_offset)
            obj["matrix"] = matrix
            (a, b, c, d, e, f) = matrix
            scaling = textstate.scaling * 0.01  # FIXME: unnecessary?
            obj["upright"] = a * d * scaling > 0 and b * c <= 0
            # Handle (rare) byte-encoded fontnames
            if isinstance(obj["fontname"], bytes):
                obj["fontname"] = fix_fontname_bytes(obj["fontname"])
        elif isinstance(content_object, PathObject):
            segments = list(content_object.segments)
            # Have to do "rect" and "line" detection ourselves, PLAYA
            # Does Not Do Heuristics
            shape = "".join(seg.operator for seg in segments)
            if shape in ("mlh", "ml"):
                obj["object_type"] = "line"
            elif (
                shape in ("mlllh", "mllll")
                and is_closed(segments)
                and is_rectangular(segments)
            ):
                obj["object_type"] = "rect"
            else:
                obj["object_type"] = "curve"

            obj["pts"] = [
                self.point2coord(seg.points[-1]) for seg in segments if seg.points
            ]
            obj["path"] = [
                (seg.operator, [self.point2coord(pt) for pt in seg.points])
                for seg in segments
            ]
            obj["evenodd"] = content_object.evenodd
            obj["stroke"] = content_object.stroke
            obj["fill"] = content_object.fill
        elif isinstance(content_object, ImageObject):
            obj["colorspace"] = content_object.colorspace
            obj["imagemask"] = content_object.imagemask
            obj["stream"] = content_object.stream
            obj["srcsize"] = content_object.srcsize
            obj["bits"] = content_object.bits
            obj["name"] = content_object.xobjid

        return obj

    def parse_playa_objects(self) -> Dict[str, T_obj_list]:
        objects: Dict[str, T_obj_list] = {}
        # TODO: flatten_contents should go in PLAYA
        for content_object in flatten_contents(self.page_obj):
            obj = self.process_playa_object(content_object)
            kind = obj["object_type"]
            if objects.get(kind) is None:
                objects[kind] = []
            objects[kind].append(obj)
        return objects

    def debug_tablefinder(
        self, table_settings: Optional[T_table_settings] = None
    ) -> TableFinder:
        tset = TableSettings.resolve(table_settings)
        return TableFinder(self, tset)

    def find_tables(
        self, table_settings: Optional[T_table_settings] = None
    ) -> List[Table]:
        tset = TableSettings.resolve(table_settings)
        return TableFinder(self, tset).tables

    def find_table(
        self, table_settings: Optional[T_table_settings] = None
    ) -> Optional[Table]:
        tset = TableSettings.resolve(table_settings)
        tables = self.find_tables(tset)

        if len(tables) == 0:
            return None

        # Return the largest table, as measured by number of cells.
        def sorter(x: Table) -> Tuple[int, T_num, T_num]:
            return (-len(x.cells), x.bbox[1], x.bbox[0])

        largest = list(sorted(tables, key=sorter))[0]

        return largest

    def extract_tables(
        self, table_settings: Optional[T_table_settings] = None
    ) -> List[List[List[Optional[str]]]]:
        tset = TableSettings.resolve(table_settings)
        tables = self.find_tables(tset)
        return [table.extract(**(tset.text_settings or {})) for table in tables]

    def extract_table(
        self, table_settings: Optional[T_table_settings] = None
    ) -> Optional[List[List[Optional[str]]]]:
        tset = TableSettings.resolve(table_settings)
        table = self.find_table(tset)
        if table is None:
            return None
        else:
            return table.extract(**(tset.text_settings or {}))

    def _get_textmap(self, **kwargs: Any) -> TextMap:
        defaults: Dict[str, Any] = dict(
            layout_bbox=self.bbox,
        )
        if "layout_width_chars" not in kwargs:
            defaults.update({"layout_width": self.width})
        if "layout_height_chars" not in kwargs:
            defaults.update({"layout_height": self.height})
        full_kwargs: Dict[str, Any] = {**defaults, **kwargs}
        return utils.chars_to_textmap(self.chars, **full_kwargs)

    def search(
        self,
        pattern: Union[str, Pattern[str]],
        regex: bool = True,
        case: bool = True,
        main_group: int = 0,
        return_chars: bool = True,
        return_groups: bool = True,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        textmap = self.get_textmap(**tuplify_list_kwargs(kwargs))
        return textmap.search(
            pattern,
            regex=regex,
            case=case,
            main_group=main_group,
            return_chars=return_chars,
            return_groups=return_groups,
        )

    def extract_text(self, **kwargs: Any) -> str:
        return self.get_textmap(**tuplify_list_kwargs(kwargs)).as_string

    def extract_text_simple(self, **kwargs: Any) -> str:
        return utils.extract_text_simple(self.chars, **kwargs)

    def extract_words(self, **kwargs: Any) -> T_obj_list:
        return utils.extract_words(self.chars, **kwargs)

    def extract_text_lines(
        self, strip: bool = True, return_chars: bool = True, **kwargs: Any
    ) -> T_obj_list:
        return self.get_textmap(**tuplify_list_kwargs(kwargs)).extract_text_lines(
            strip=strip, return_chars=return_chars
        )

    def crop(
        self, bbox: T_bbox, relative: bool = False, strict: bool = True
    ) -> "CroppedPage":
        return CroppedPage(self, bbox, relative=relative, strict=strict)

    def within_bbox(
        self, bbox: T_bbox, relative: bool = False, strict: bool = True
    ) -> "CroppedPage":
        """
        Same as .crop, except only includes objects fully within the bbox
        """
        return CroppedPage(
            self, bbox, relative=relative, strict=strict, crop_fn=utils.within_bbox
        )

    def outside_bbox(
        self, bbox: T_bbox, relative: bool = False, strict: bool = True
    ) -> "CroppedPage":
        """
        Same as .crop, except only includes objects fully within the bbox
        """
        return CroppedPage(
            self, bbox, relative=relative, strict=strict, crop_fn=utils.outside_bbox
        )

    def filter(self, test_function: Callable[[T_obj], bool]) -> "FilteredPage":
        return FilteredPage(self, test_function)

    def dedupe_chars(self, **kwargs: Any) -> "FilteredPage":
        """
        Removes duplicate chars — those sharing the same text and positioning
        (within `tolerance`) as other characters in the set. Adjust extra_args
        to be more/less restrictive with the properties checked.
        """
        p = FilteredPage(self, lambda x: True)
        p._objects = {kind: objs for kind, objs in self.objects.items()}
        p._objects["char"] = utils.dedupe_chars(self.chars, **kwargs)
        return p

    def to_image(
        self,
        resolution: Optional[Union[int, float]] = None,
        width: Optional[Union[int, float]] = None,
        height: Optional[Union[int, float]] = None,
        antialias: bool = False,
        force_mediabox: bool = False,
    ) -> "PageImage":
        """
        You can pass a maximum of 1 of the following:
        - resolution: The desired number pixels per inch. Defaults to 72.
        - width: The desired image width in pixels.
        - height: The desired image width in pixels.
        """
        from .display import DEFAULT_RESOLUTION, PageImage

        num_specs = sum(x is not None for x in [resolution, width, height])
        if num_specs > 1:
            raise ValueError(
                f"Only one of these arguments can be provided: resolution, width, height. You provided {num_specs}"  # noqa: E501
            )
        elif width is not None:
            resolution = 72 * width / self.width
        elif height is not None:
            resolution = 72 * height / self.height

        return PageImage(
            self,
            resolution=resolution or DEFAULT_RESOLUTION,
            antialias=antialias,
            force_mediabox=force_mediabox,
        )

    def to_dict(self, object_types: Optional[List[str]] = None) -> Dict[str, Any]:
        if object_types is None:
            _object_types = list(self.objects.keys()) + ["annot"]
        else:
            _object_types = object_types
        d = {
            "page_number": self.page_number,
            "initial_doctop": self.initial_doctop,
            "rotation": self.rotation,
            "cropbox": self.cropbox,
            "mediabox": self.mediabox,
            "bbox": self.bbox,
            "width": self.width,
            "height": self.height,
        }
        for t in _object_types:
            d[t + "s"] = getattr(self, t + "s")
        return d

    def __repr__(self) -> str:
        return f"<Page:{self.page_number}>"


class DerivedPage(Page):
    is_original: bool = False

    def __init__(self, parent_page: Page):
        self.parent_page = parent_page
        self.root_page = parent_page.root_page
        self.pdf = parent_page.pdf
        self.page_obj = parent_page.page_obj
        self.page_number = parent_page.page_number
        self.initial_doctop = parent_page.initial_doctop
        self.rotation = parent_page.rotation
        self.mediabox = parent_page.mediabox
        self.cropbox = parent_page.cropbox
        self.flush_cache(Container.cached_properties)
        self.get_textmap = lru_cache()(self._get_textmap)


def test_proposed_bbox(bbox: T_bbox, parent_bbox: T_bbox) -> None:
    bbox_area = utils.calculate_area(bbox)
    if bbox_area == 0:
        raise ValueError(f"Bounding box {bbox} has an area of zero.")

    overlap = utils.get_bbox_overlap(bbox, parent_bbox)
    if overlap is None:
        raise ValueError(
            f"Bounding box {bbox} is entirely outside "
            f"parent page bounding box {parent_bbox}"
        )

    overlap_area = utils.calculate_area(overlap)
    if overlap_area < bbox_area:
        raise ValueError(
            f"Bounding box {bbox} is not fully within "
            f"parent page bounding box {parent_bbox}"
        )


class CroppedPage(DerivedPage):
    def __init__(
        self,
        parent_page: Page,
        crop_bbox: T_bbox,
        crop_fn: Callable[[T_obj_list, T_bbox], T_obj_list] = utils.crop_to_bbox,
        relative: bool = False,
        strict: bool = True,
    ):
        if relative:
            o_x0, o_top, _, _ = parent_page.bbox
            x0, top, x1, bottom = crop_bbox
            crop_bbox = (x0 + o_x0, top + o_top, x1 + o_x0, bottom + o_top)

        if strict:
            test_proposed_bbox(crop_bbox, parent_page.bbox)

        def _crop_fn(objs: T_obj_list) -> T_obj_list:
            return crop_fn(objs, crop_bbox)

        super().__init__(parent_page)

        self._crop_fn = _crop_fn

        # Note: testing for original function passed, not _crop_fn
        if crop_fn is utils.outside_bbox:
            self.bbox = parent_page.bbox
        else:
            self.bbox = crop_bbox

    @property
    def objects(self) -> Dict[str, T_obj_list]:
        if hasattr(self, "_objects"):
            return self._objects
        self._objects: Dict[str, T_obj_list] = {
            k: self._crop_fn(v) for k, v in self.parent_page.objects.items()
        }
        return self._objects


class FilteredPage(DerivedPage):
    def __init__(self, parent_page: Page, filter_fn: Callable[[T_obj], bool]):
        self.bbox = parent_page.bbox
        self.filter_fn = filter_fn
        super().__init__(parent_page)

    @property
    def objects(self) -> Dict[str, T_obj_list]:
        if hasattr(self, "_objects"):
            return self._objects
        self._objects: Dict[str, T_obj_list] = {
            k: list(filter(self.filter_fn, v))
            for k, v in self.parent_page.objects.items()
        }
        return self._objects
