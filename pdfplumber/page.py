from . import utils
from .utils import resolve_all
from .table import TableFinder
from .container import Container
from copy import copy

import re
lt_pat = re.compile(r"^LT")


class Page(Container):
    cached_properties = Container.cached_properties + [ "_layout" ]
    is_original = True

    def __init__(self, pdf, page_obj, page_number=None, initial_doctop=0):
        self.pdf = pdf
        self.page_obj = page_obj
        self.page_number = page_number
        _rotation = self.decimalize(resolve_all(self.page_obj.attrs.get("Rotate", 0)))
        self.rotation =  _rotation % 360
        self.page_obj.rotate = self.rotation
        self.initial_doctop = self.decimalize(initial_doctop)

        cropbox = page_obj.attrs.get("CropBox")
        mediabox = page_obj.attrs.get("MediaBox")

        self.cropbox = self.decimalize(resolve_all(cropbox)) if cropbox is not None else None
        self.mediabox = self.decimalize(resolve_all(mediabox) or self.cropbox)
        m = self.mediabox

        if self.rotation in [ 90, 270 ]:
            self.bbox = self.decimalize((
                min(m[1], m[3]),
                min(m[0], m[2]),
                max(m[1], m[3]),
                max(m[0], m[2]),
            ))
        else:
            self.bbox = self.decimalize((
                min(m[0], m[2]),
                min(m[1], m[3]),
                max(m[0], m[2]),
                max(m[1], m[3]),
            ))

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
        if hasattr(self, "_layout"): return self._layout
        self._layout = self.pdf.process_page(self.page_obj)
        return self._layout

    @property
    def objects(self):
        if hasattr(self, "_objects"): return self._objects
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
            return (
                d(x),
                h - d(y)
            )

        noop = lambda x: x
        str_conv = lambda x: str(x or "")

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
            attr = dict((k, CONVERSIONS[k](resolve_all(v)))
                for k, v in obj.__dict__.items()
                    if k in CONVERSIONS_KEYS)

            kind = re.sub(lt_pat, "", obj.__class__.__name__).lower()
            attr["object_type"] = kind
            attr["page_number"] = pno

            if hasattr(obj, "get_text"):
                attr["text"] = obj.get_text()

            if kind == "curve":
                attr["points"] = list(map(point2coord, obj.pts))

            if attr.get("y0") != None:
                attr["top"] = h - attr["y1"]
                attr["bottom"] = h - attr["y0"]
                attr["doctop"] = idc + attr["top"]

            if objects.get(kind) == None:
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

        extract_kwargs = dict((k, table_settings["text_" + k]) for k in [
            "x_tolerance",
            "y_tolerance",
        ] if "text_" + k in table_settings)

        return [ table.extract(**extract_kwargs) for table in tables ]

    def extract_table(self, table_settings={}):
        tables = self.find_tables(table_settings)
        
        if len(tables) == 0:
            return None

        # Return the largest table, as measured by number of cells.
        sorter = lambda x: (-len(x.cells), x.bbox[1], x.bbox[0])
        largest = list(sorted(tables, key=sorter))[0]
        return largest.extract()

    def extract_text(self,
        x_tolerance=utils.DEFAULT_X_TOLERANCE,
        y_tolerance=utils.DEFAULT_Y_TOLERANCE):

        return utils.extract_text(self.chars,
            x_tolerance=x_tolerance,
            y_tolerance=y_tolerance)

    def extract_words(self,
        x_tolerance=utils.DEFAULT_X_TOLERANCE,
        y_tolerance=utils.DEFAULT_Y_TOLERANCE,
        keep_blank_chars=False):

        return utils.extract_words(self.chars,
            x_tolerance=x_tolerance,
            y_tolerance=y_tolerance,
            keep_blank_chars=keep_blank_chars)

    def crop(self, bbox):
        class CroppedPage(DerivedPage):
            @property
            def objects(self):
                if hasattr(self, "_objects"): return self._objects
                self._objects = utils.crop_to_bbox(
                    self.parent_page.objects,
                    self.bbox)
                return self._objects

        cropped = CroppedPage(self)
        cropped.bbox = self.decimalize(bbox)
        return cropped

    def within_bbox(self, bbox):
        """
        Same as .crop, except only includes objects fully within the bbox
        """
        class CroppedPage(DerivedPage):
            @property
            def objects(self):
                if hasattr(self, "_objects"): return self._objects
                self._objects = utils.within_bbox(
                    self.parent_page.objects,
                    self.bbox)
                return self._objects

        cropped = CroppedPage(self)
        cropped.bbox = self.decimalize(bbox)
        return cropped

    def filter(self, test_function):
        class FilteredPage(DerivedPage):
            @property
            def objects(self):
                if hasattr(self, "_objects"): return self._objects
                self._objects = utils.filter_objects(
                    self.parent_page.objects,
                    test_function
                )
                return self._objects
        filtered = FilteredPage(self)
        filtered.bbox = self.bbox
        return filtered

    def to_image(self, **conversion_kwargs):
        """
        For conversion_kwargs, see http://docs.wand-py.org/en/latest/wand/image.html#wand.image.Image
        """
        from .display import PageImage, DEFAULT_RESOLUTION
        kwargs = dict(conversion_kwargs)
        if "resolution" not in conversion_kwargs:
            kwargs["resolution"] = DEFAULT_RESOLUTION
        return PageImage(self, **kwargs)

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
