from . import utils
from .utils import resolve_all
from .table import TableFinder
from .container import Container
import re

lt_pat = re.compile(r"^LT")


class Page(Container):
    cached_properties = Container.cached_properties + ["_layout"]
    is_original = True

    def __init__(self, pdf, page_obj, page_number=None, initial_doctop=0):
        self.pdf = pdf
        self.page_obj = page_obj
        self.page_number = page_number
        _rotation = self.decimalize(resolve_all(self.page_obj.attrs.get("Rotate", 0)))
        self.rotation = _rotation % 360
        self.page_obj.rotate = self.rotation
        self.initial_doctop = self.decimalize(initial_doctop)

        cropbox = page_obj.attrs.get("CropBox")
        mediabox = page_obj.attrs.get("MediaBox")

        self.cropbox = (
            self.decimalize(resolve_all(cropbox)) if cropbox is not None else None
        )
        self.mediabox = self.decimalize(resolve_all(mediabox) or self.cropbox)
        m = self.mediabox

        if self.rotation in [90, 270]:
            self.bbox = self.decimalize(
                (min(m[1], m[3]), min(m[0], m[2]), max(m[1], m[3]), max(m[0], m[2]),)
            )
        else:
            self.bbox = self.decimalize(
                (min(m[0], m[2]), min(m[1], m[3]), max(m[0], m[2]), max(m[1], m[3]),)
            )

    def decimalize(self, x):
        return utils.decimalize(x, self.pdf.precision)

    @property
    def width(self):
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self):
        return self.bbox[3] - self.bbox[1]

    @property
    def layout(self):
        if hasattr(self, "_layout"):
            return self._layout
        self._layout = self.pdf.process_page(self.page_obj)
        return self._layout

    @property
    def annots(self):
        def parse(annot):
            rect = self.decimalize(annot["Rect"])

            a = annot.get("A", {})
            extras = {
                "uri": a.get("URI"),
                "title": annot.get("T"),
                "contents": annot.get("Contents"),
            }
            for k, v in extras.items():
                if v is not None:
                    extras[k] = v.decode("utf-8")

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
    def hyperlinks(self):
        return [a for a in self.annots if a["uri"] is not None]

    @property
    def objects(self):
        if hasattr(self, "_objects"):
            return self._objects
        self._objects = self.parse_objects()
        return self._objects

    def parse_objects(self):
        objects = {}

        d = self.decimalize
        h = self.height
        idc = self.initial_doctop
        pno = self.page_number

        def point2coord(pt):
            x, y = pt
            return (d(x), h - d(y))

        def noop(x):
            return x

        def str_conv(x):
            return str(x or "")

        CONVERSIONS = {
            # Decimals
            "adv": d,
            "height": d,
            "linewidth": d,
            "pts": d,
            "size": d,
            "srcsize": d,
            "width": d,
            "x0": d,
            "x1": d,
            "y0": d,
            "y1": d,
            # Integer
            "bits": int,
            "upright": int,
            # Strings
            "font": str_conv,
            "fontname": str_conv,
            "name": str_conv,
            "object_type": str_conv,
            "text": str_conv,
            # No conversion
            "imagemask": noop,
            "colorspace": noop,
            "evenodd": noop,
            "fill": noop,
            "non_stroking_color": noop,
            "path": noop,
            "stream": noop,
            "stroke": noop,
            "stroking_color": noop,
        }

        CONVERSIONS_KEYS = set(CONVERSIONS.keys())

        def process_object(obj):
            attr = dict(
                (k, CONVERSIONS[k](resolve_all(v)))
                for k, v in obj.__dict__.items()
                if k in CONVERSIONS_KEYS
            )

            kind = re.sub(lt_pat, "", obj.__class__.__name__).lower()
            attr["object_type"] = kind
            attr["page_number"] = pno

            if hasattr(obj, "graphicstate"):
                gs = obj.graphicstate
                attr["stroking_color"] = gs.scolor
                attr["non_stroking_color"] = gs.ncolor

            if hasattr(obj, "get_text"):
                attr["text"] = obj.get_text()

            if kind == "curve":
                attr["points"] = list(map(point2coord, obj.pts))

            if attr.get("y0") is not None:
                attr["top"] = h - attr["y1"]
                attr["bottom"] = h - attr["y0"]
                attr["doctop"] = idc + attr["top"]

            if objects.get(kind) is None:
                objects[kind] = []
            objects[kind].append(attr)

            if hasattr(obj, "_objs"):
                for child in obj._objs:
                    process_object(child)

        for obj in self.layout._objs:
            process_object(obj)

        return objects

    def debug_tablefinder(self, table_settings={}):
        return TableFinder(self, table_settings)

    def find_tables(self, table_settings={}):
        return TableFinder(self, table_settings).tables

    def extract_tables(self, table_settings={}):
        tables = self.find_tables(table_settings)

        extract_kwargs = dict(
            (k, table_settings["text_" + k])
            for k in ["x_tolerance", "y_tolerance"]
            if "text_" + k in table_settings
        )

        return [table.extract(**extract_kwargs) for table in tables]

    def extract_table(self, table_settings={}):
        tables = self.find_tables(table_settings)

        if len(tables) == 0:
            return None

        # Return the largest table, as measured by number of cells.
        def sorter(x):
            return (-len(x.cells), x.bbox[1], x.bbox[0])

        largest = list(sorted(tables, key=sorter))[0]
        return largest.extract()

    def extract_text(self, **kwargs):
        return utils.extract_text(self.chars, **kwargs)

    def extract_words(self, **kwargs):
        return utils.extract_words(self.chars, **kwargs)

    def crop(self, bbox, relative=False):
        return CroppedPage(self, self.decimalize(bbox), relative=relative)

    def within_bbox(self, bbox, relative=False):
        """
        Same as .crop, except only includes objects fully within the bbox
        """
        return CroppedPage(
            self, self.decimalize(bbox), relative=relative, crop_fn=utils.within_bbox
        )

    def filter(self, test_function):
        return FilteredPage(self, test_function)

    def to_image(self, **conversion_kwargs):
        """
        For conversion_kwargs, see:
        http://docs.wand-py.org/en/latest/wand/image.html#wand.image.Image
        """
        from .display import PageImage, DEFAULT_RESOLUTION

        kwargs = dict(conversion_kwargs)
        if "resolution" not in conversion_kwargs:
            kwargs["resolution"] = DEFAULT_RESOLUTION
        return PageImage(self, **kwargs)

    def __repr__(self):
        return f"<Page:{self.page_number}>"


class DerivedPage(Page):
    is_original = False

    def __init__(self, parent_page):
        self.parent_page = parent_page
        self.pdf = parent_page.pdf
        self.page_obj = parent_page.page_obj
        self.page_number = parent_page.page_number
        self.flush_cache(Container.cached_properties)

        if type(parent_page) == Page:
            self.root_page = parent_page
        else:
            self.root_page = parent_page.root_page


def test_proposed_bbox(bbox, parent_bbox):
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
    def __init__(self, parent_page, bbox, crop_fn=utils.crop_to_bbox, relative=False):
        if relative:
            o_x0, o_top, _, _ = parent_page.bbox
            x0, top, x1, bottom = bbox
            self.bbox = (x0 + o_x0, top + o_top, x1 + o_x0, bottom + o_top)
        else:
            self.bbox = bbox

        test_proposed_bbox(self.bbox, parent_page.bbox)
        self.crop_fn = crop_fn
        super().__init__(parent_page)

    @property
    def objects(self):
        if hasattr(self, "_objects"):
            return self._objects
        self._objects = self.crop_fn(self.parent_page.objects, self.bbox)
        return self._objects


class FilteredPage(DerivedPage):
    def __init__(self, parent_page, filter_fn):
        self.bbox = parent_page.bbox
        self.filter_fn = filter_fn
        super().__init__(parent_page)

    @property
    def objects(self):
        if hasattr(self, "_objects"):
            return self._objects
        self._objects = utils.filter_objects(self.parent_page.objects, self.filter_fn)
        return self._objects
