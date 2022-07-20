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
    LTCurve,
    LTItem,
    LTLine,
    LTPage,
    LTRect,
)
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfpage import PDFPage

from . import utils
from ._typing import T_bbox, T_num, T_obj, T_obj_list
from .container import Container
from .table import T_table_settings, Table, TableFinder, TableSettings
from .utils import resolve_all

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
        "font",
        "fontname",
        "name",
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
    ]
)


if TYPE_CHECKING:  # pragma: nocover
    from .display import PageImage
    from .pdf import PDF


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
        _rotation = resolve_all(self.page_obj.attrs.get("Rotate", 0))
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
        device = PDFPageAggregator(
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

        if isinstance(obj, LTChar):
            attr["text"] = obj.get_text()
            gs = obj.graphicstate
            attr["stroking_color"] = gs.scolor
            attr["non_stroking_color"] = gs.ncolor

        if isinstance(obj, LTCurve) and not isinstance(obj, (LTRect, LTLine)):

            def point2coord(pt: Tuple[T_num, T_num]) -> Tuple[T_num, T_num]:
                x, y = pt
                return (x, self.height - y)

            attr["points"] = list(map(point2coord, obj.pts))

        if attr.get("y0") is not None:
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

    def extract_tables(
        self, table_settings: Optional[T_table_settings] = None
    ) -> List[List[List[Optional[str]]]]:
        tset = TableSettings.resolve(table_settings)
        tables = self.find_tables(tset)

        extract_kwargs = {
            k: getattr(tset, "text_" + k) for k in ["x_tolerance", "y_tolerance"]
        }

        return [table.extract(**extract_kwargs) for table in tables]

    def extract_table(
        self, table_settings: Optional[T_table_settings] = None
    ) -> Optional[List[List[Optional[str]]]]:
        tset = TableSettings.resolve(table_settings)
        tables = self.find_tables(tset)

        if len(tables) == 0:
            return None

        # Return the largest table, as measured by number of cells.
        def sorter(x: Table) -> Tuple[int, T_num, T_num]:
            return (-len(x.cells), x.bbox[1], x.bbox[0])

        largest = list(sorted(tables, key=sorter))[0]

        extract_kwargs = {
            k: getattr(tset, "text_" + k) for k in ["x_tolerance", "y_tolerance"]
        }

        return largest.extract(**extract_kwargs)

    @lru_cache()
    def get_text_layout(self, **kwargs: Any) -> utils.TextLayout:
        defaults = dict(x_shift=self.bbox[0], y_shift=self.bbox[1])
        full_kwargs: Dict[str, Any] = {**defaults, **kwargs}
        return utils.chars_to_layout(self.chars, **full_kwargs)

    def search(
        self,
        pattern: Union[str, Pattern[str]],
        regex: bool = True,
        case: bool = True,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        text_layout = self.get_text_layout(**kwargs)
        return text_layout.search(pattern, regex=regex, case=case)

    def extract_text(self, **kwargs: Any) -> str:
        if kwargs.get("layout") is True:
            del kwargs["layout"]
            text_layout = self.get_text_layout(**kwargs)
            return text_layout.to_string()
        else:
            return utils.extract_text(self.chars, **kwargs)

    def extract_words(self, **kwargs: Any) -> T_obj_list:
        return utils.extract_words(self.chars, **kwargs)

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
        p = CroppedPage(
            self, bbox, relative=relative, strict=strict, crop_fn=utils.outside_bbox
        )

        # Reset, because this operation should not actually change bbox
        p.bbox = self.bbox
        return p

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

    def to_image(self, **conversion_kwargs: Any) -> "PageImage":
        """
        For conversion_kwargs, see:
        http://docs.wand-py.org/en/latest/wand/image.html#wand.image.Image
        """
        from .display import DEFAULT_RESOLUTION, PageImage

        kwargs = dict(conversion_kwargs)
        if "resolution" not in conversion_kwargs:
            kwargs["resolution"] = DEFAULT_RESOLUTION
        return PageImage(self, **kwargs)

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
        bbox: T_bbox,
        crop_fn: Callable[[T_obj_list, T_bbox], T_obj_list] = utils.crop_to_bbox,
        relative: bool = False,
        strict: bool = True,
    ):
        if relative:
            o_x0, o_top, _, _ = parent_page.bbox
            x0, top, x1, bottom = bbox
            self.bbox = (x0 + o_x0, top + o_top, x1 + o_x0, bottom + o_top)
        else:
            self.bbox = bbox

        if strict:
            test_proposed_bbox(self.bbox, parent_page.bbox)

        def _crop_fn(objs: T_obj_list) -> T_obj_list:
            return crop_fn(objs, bbox)

        self._crop_fn = _crop_fn

        super().__init__(parent_page)

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
