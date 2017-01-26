from pdfplumber import utils
from pdfplumber.container import Container

from six import string_types
import re
lt_pat = re.compile(r"^LT")

class Page(Container):
    cached_properties = Container.cached_properties + [ "_layout" ]

    def __init__(self, pdf, page_obj, page_number=None, initial_doctop=0):
        self.pdf = pdf
        self.page_obj = page_obj
        self.page_number = page_number
        self.page_obj.rotate = self.page_obj.attrs.get("Rotate", 0) % 360
        self.layout = self.pdf.process_page(self.page_obj)
        self.initial_doctop = self.decimalize(initial_doctop)

        cropbox = page_obj.attrs.get("CropBox", page_obj.attrs.get("MediaBox"))
        self.cropbox = tuple(map(self.decimalize, cropbox))
        self.bbox = self.layout.bbox
        x0, bottom, x1, top = self.bbox
        width = x1 - x0
        height = top - bottom

    def decimalize(self, x):
        return utils.decimalize(x, self.pdf.precision)

    @property
    def width(self):
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self):
        return self.bbox[3] - self.bbox[1]

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

        def process_object(obj):

            attr = dict((k, d(v)) for k, v in obj.__dict__.items()
                if isinstance(v, (float, int, string_types))
                    and k[0] != "_")

            kind = re.sub(lt_pat, "", obj.__class__.__name__).lower()
            attr["object_type"] = kind
            attr["page_number"] = pno

            if hasattr(obj, "get_text"):
                attr["text"] = obj.get_text()

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

    def filter_edges(self, orientation,
        edge_type=None,
        min_length=1):

        if orientation not in ("v", "h"):
            raise Exception("Orientation must be 'v' or 'h'")

        def test(e):
            dim = "height" if e["orientation"] == "v" else "width"
            et = (e["object_type"] == edge_type if edge_type != None else True)
            return et & (
                (e["orientation"] == orientation) & 
                (e[dim] >= min_length)
            )

        edges = filter(test, self.edges)
        return edges

    def get_edge_positions(self, orientation,
        edge_type=None,
        min_length=1,
        tolerance=1):

        edges = self.filter_edges(orientation,
            edge_type=edge_type, min_length=min_length)

        pos_var = "x0" if orientation == "v" else "top"
        edges_uniq = set(e[pos_var] for e in edges)
        edges_clust = utils.cluster_list(edges_uniq, tolerance=tolerance)
        edge_means = list(sorted(sum(c) / len(c) for c in edges_clust))

        return edge_means

    TABLE_STRATEGIES = ("lines", "lines_strict", "gutters")
    def extract_table(self,
        v="lines",
        h="lines",
        line_min_height=1,
        line_min_width=1,
        gutter_min_width=5,
        gutter_min_height=5,
        x_tolerance=utils.DEFAULT_X_TOLERANCE,
        y_tolerance=utils.DEFAULT_Y_TOLERANCE):
        """
        For the purposes of this method, "lines" refers to all
        two-dimensional lines, including "rect_edge" objects.

        To use only actual "line" objects, choose the
        "lines_strict" strategy.
        """

        def use_strategy(param, name):
            # If dividers are explicitly passed
            if isinstance(param, (list, tuple)):
                return param
            else:
                if param not in self.TABLE_STRATEGIES:
                    msg = "{0} must be list/tuple of ints/floats or one of {1}"\
                        .format(name, self.TABLE_STRATEGIES)
                    raise ValueError(msg)

            if param == "lines":
                if name == "v":
                    return self.get_edge_positions("v",
                        min_length=line_min_height,
                        tolerance=x_tolerance)
                if name == "h":
                    return self.get_edge_positions("h",
                        min_length=line_min_width,
                        tolerance=y_tolerance)

            if param == "lines_strict":
                if name == "v":
                    return self.get_edge_positions("v",
                        edge_type="line",
                        min_length=line_min_height,
                        tolerance=x_tolerance)
                if name == "h":
                    return self.get_edge_positions("h",
                        edge_type="line",
                        min_length=line_min_width,
                        tolerance=y_tolerance)

            if param == "gutters":
                if name == "v":
                    return utils.find_gutters(self.chars, "v",
                        min_size=gutter_min_width)
                if name == "h":
                    return utils.find_gutters(self.chars, "h",
                        min_size=gutter_min_height)

        h = list(map(self.decimalize, use_strategy(h, "h")))
        v = list(map(self.decimalize, use_strategy(v, "v")))

        table = utils.extract_table(self.chars, v, h,
            x_tolerance=x_tolerance,
            y_tolerance=y_tolerance)

        return table

    def extract_text(self,
        x_tolerance=utils.DEFAULT_X_TOLERANCE,
        y_tolerance=utils.DEFAULT_Y_TOLERANCE):

        return utils.extract_text(self.chars,
            x_tolerance=x_tolerance,
            y_tolerance=y_tolerance)

    def extract_words(self,
        x_tolerance=utils.DEFAULT_X_TOLERANCE,
        y_tolerance=utils.DEFAULT_Y_TOLERANCE):

        return utils.extract_words(self.chars,
            x_tolerance=x_tolerance,
            y_tolerance=y_tolerance)

    def crop(self, bbox, strict=False):
        return CroppedPage(self, bbox, strict=strict)

    def filter(self, fn):
        return FilteredPage(self, fn)

class CroppedPage(Page):
    def __init__(self, parent_page, bbox, strict=False):
        self.parent_page = parent_page
        self.page_number = parent_page.page_number
        self.page_number = parent_page.page_number
        self.decimalize = parent_page.decimalize

        self.bbox = bbox
        self.strict = strict

    @property
    def objects(self):
        if hasattr(self, "_objects"): return self._objects
        if self.strict:
            kwargs = { "strict": True }
        else:
            kwargs = { "crop": True }
        self._objects = utils.within_bbox(
            self.parent_page.objects,
            self.bbox,
            **kwargs)
        return self._objects

class FilteredPage(Page):
    def __init__(self, parent_page, test_function):
        self.parent_page = parent_page
        self.test_function = test_function

        self.page_number = parent_page.page_number
        self.page_number = parent_page.page_number
        self.decimalize = parent_page.decimalize

    @property
    def objects(self):
        if hasattr(self, "_objects"): return self._objects
        self._objects = utils.filter_objects(
            self.parent_page.objects,
            self.test_function
        )
        return self._objects
