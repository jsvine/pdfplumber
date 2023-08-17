import re
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Pattern,
    Tuple,
    Union,
)

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import (
    LTChar,
    LTComponent,
    LTContainer,
    LTItem,
    LTPage,
    LTTextContainer,
)
from pdfminer.pdfinterp import PDFPageInterpreter, PDFStackT
from pdfminer.pdfpage import PDFPage
from pdfminer.psparser import PSLiteral

from . import utils
from ._typing import T_bbox, T_num, T_obj, T_obj_list
from .container import Container
from .table import T_table_settings, Table, TableFinder, TableSettings
from .utils import decode_text, resolve_all, resolve_and_decode
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
        "imagemask",
        "colorspace",
        "evenodd",
        "fill",
        "non_stroking_color",
        "path",
        "stream",
        "stroke",
        "stroking_color",
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
    color: Tuple[Any, ...]
) -> Tuple[Optional[Tuple[Union[float, int], ...]], Optional[str]]:
    if isinstance(color[-1], PSLiteral):
        return (color[:-1] or None), decode_text(color[-1].name)
    else:
        return color, None


def normalize_color(
    color: Any,
) -> Tuple[Optional[Tuple[Union[float, int], ...]], Optional[str]]:
    if color is None:
        return (None, None)
    elif isinstance(color, tuple):
        tuplefied = color
    elif isinstance(color, list):
        tuplefied = tuple(color)
    else:
        tuplefied = (color,)
    return separate_pattern(tuplefied)


class PDFPageAggregatorWithMarkedContent(PDFPageAggregator):
    """Extract layout from a specific page, adding marked-content IDs to
    objects where found."""

    cur_mcid: Optional[int] = None
    cur_tag: Optional[str] = None

    def begin_tag(self, tag: PSLiteral, props: Optional[PDFStackT] = None) -> None:
        """Handle beginning of tag, setting current MCID if any."""
        self.cur_tag = decode_text(tag.name)
        if isinstance(props, dict) and "MCID" in props:
            self.cur_mcid = props["MCID"]
        else:
            self.cur_mcid = None

    def end_tag(self) -> None:
        """Handle beginning of tag, clearing current MCID."""
        self.cur_tag = None
        self.cur_mcid = None

    def tag_cur_item(self) -> None:
        """Add current MCID to what we hope to be the most recent object created
        by pdfminer.six."""
        # This is somewhat hacky and would not be necessary if
        # pdfminer.six supported MCIDs.  In reading the code it's
        # clear that the `render_*` methods methods will only ever
        # create one object, but that is far from being guaranteed.
        # Even if pdfminer.six's API would just return the objects it
        # creates, we wouldn't have to do this.
        cur_obj = self.cur_item._objs[-1]
        cur_obj.mcid = self.cur_mcid  # type: ignore
        cur_obj.tag = self.cur_tag  # type: ignore

    def render_char(self, *args, **kwargs) -> float:  # type: ignore
        """Hook for rendering characters, adding the `mcid` attribute."""
        adv = super().render_char(*args, **kwargs)
        self.tag_cur_item()
        return adv

    def render_image(self, *args, **kwargs) -> None:  # type: ignore
        """Hook for rendering images, adding the `mcid` attribute."""
        super().render_image(*args, **kwargs)
        self.tag_cur_item()

    def paint_path(self, *args, **kwargs) -> None:  # type: ignore
        """Hook for rendering lines and curves, adding the `mcid` attribute."""
        super().paint_path(*args, **kwargs)
        self.tag_cur_item()


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
        _rotation = resolve_all(self.page_obj.attrs.get("Rotate", 0)) or 0
        self.rotation = _rotation % 360
        self.page_obj.rotate = self.rotation
        self.initial_doctop = initial_doctop

        cropbox = page_obj.attrs.get("CropBox")
        mediabox = page_obj.attrs.get("MediaBox")

        self.cropbox = resolve_all(cropbox) if cropbox is not None else None
        self.mediabox = resolve_all(mediabox) or self.cropbox
        m = self.mediabox

        self.bbox: T_bbox = (
            (
                min(m[1], m[3]),
                min(m[0], m[2]),
                max(m[1], m[3]),
                max(m[0], m[2]),
            )
            if self.rotation in [90, 270]
            else (
                min(m[0], m[2]),
                min(m[1], m[3]),
                max(m[0], m[2]),
                max(m[1], m[3]),
            )
        )

        # https://rednafi.github.io/reflections/dont-wrap-instance-methods-with-functoolslru_cache-decorator-in-python.html
        self.get_textmap = lru_cache()(self._get_textmap)

    @property
    def width(self) -> T_num:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> T_num:
        return self.bbox[3] - self.bbox[1]

    @property
    def layout(self) -> LTPage:
        if hasattr(self, "_layout"):
            return self._layout
        device = PDFPageAggregatorWithMarkedContent(
            self.pdf.rsrcmgr,
            pageno=self.page_number,
            laparams=self.pdf.laparams,
        )
        interpreter = PDFPageInterpreter(self.pdf.rsrcmgr, device)
        interpreter.process_page(self.page_obj)
        self._layout: LTPage = device.get_result()
        return self._layout

    @property
    def annots(self) -> T_obj_list:
        def parse(annot: T_obj) -> T_obj:
            rect = annot["Rect"]

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
                        extras[k] = v.decode("utf-16")

            parsed = {
                "page_number": self.page_number,
                "object_type": "annot",
                "x0": rect[0],
                "y0": rect[1],
                "x1": rect[2],
                "y1": rect[3],
                "doctop": self.initial_doctop + self.height - rect[3],
                "top": self.height - rect[3],
                "bottom": self.height - rect[1],
                "width": rect[2] - rect[0],
                "height": rect[3] - rect[1],
            }
            parsed.update(extras)
            # Replace the indirect reference to the page dictionary
            # with a pointer to our actual page
            if "P" in annot:
                annot["P"] = self
            parsed["data"] = annot
            return parsed

        raw = resolve_all(self.page_obj.annots) or []
        return list(map(parse, raw))

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
        return (pt[0], self.height - pt[1])

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

        for cs in ["ncs", "scs"]:
            # Note: As of pdfminer.six v20221105, that library only
            # exposes ncs for LTChars, and neither attribute for
            # other objects. Keeping this code here, though,
            # for ease of addition if color spaces become
            # more available via pdfminer.six
            if hasattr(obj, cs):
                attr[cs] = resolve_and_decode(getattr(obj, cs).name)

        for color_attr, pattern_attr in [
            ("stroking_color", "stroking_pattern"),
            ("non_stroking_color", "non_stroking_pattern"),
        ]:
            if color_attr in attr:
                attr[color_attr], attr[pattern_attr] = normalize_color(attr[color_attr])

        if isinstance(obj, (LTChar, LTTextContainer)):
            attr["text"] = obj.get_text()

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

        if "pts" in attr:
            attr["pts"] = list(map(self.point2coord, attr["pts"]))

        if "y0" in attr:
            attr["top"] = self.height - attr["y1"]
            attr["bottom"] = self.height - attr["y0"]
            attr["doctop"] = self.initial_doctop + attr["top"]

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
        for obj in self.iter_layout_objects(self.layout._objs):
            kind = obj["object_type"]
            if kind in ["anno"]:
                continue
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
        defaults = dict(x_shift=self.bbox[0], y_shift=self.bbox[1])
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
        textmap = self.get_textmap(**kwargs)
        return textmap.search(
            pattern,
            regex=regex,
            case=case,
            main_group=main_group,
            return_chars=return_chars,
            return_groups=return_groups,
        )

    def extract_text(self, **kwargs: Any) -> str:
        return self.get_textmap(**kwargs).as_string

    def extract_text_simple(self, **kwargs: Any) -> str:
        return utils.extract_text_simple(self.chars, **kwargs)

    def extract_words(self, **kwargs: Any) -> T_obj_list:
        return utils.extract_words(self.chars, **kwargs)

    def extract_text_lines(
        self, strip: bool = True, return_chars: bool = True, **kwargs: Any
    ) -> T_obj_list:
        return self.get_textmap(**kwargs).extract_text_lines(
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
        Removes duplicate chars — those sharing the same text, fontname, size,
        and positioning (within `tolerance`) as other characters on the page.
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
            self, resolution=resolution or DEFAULT_RESOLUTION, antialias=antialias
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
