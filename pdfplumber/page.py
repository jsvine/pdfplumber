from pdfplumber import utils
from pdfplumber import helpers
from pdfplumber.container import Container

from six import string_types
import re
lt_pat = re.compile(r"^LT")

TABLE_STRATEGIES = ("lines", "lines_strict", "gutters")

class Page(Container):
    cached_properties = Container.cached_properties + [ "_layout" ]

    def __init__(self, obj, processor, initial_doctop=0):
        self.obj = obj
        self.processor = processor
        self.mediabox = obj.attrs["MediaBox"]
        self.width = self.mediabox[2] - self.mediabox[0]
        self.height = self.mediabox[3] - self.mediabox[1]
        self.pageid = obj.pageid
        self.initial_doctop = initial_doctop

    @property
    def layout(self):
        if hasattr(self, "_layout"): return self._layout
        self._layout = self.processor(self.obj)
        return self._layout

    @property
    def objects(self):
        if hasattr(self, "_objects"): return self._objects
        self._objects = self.parse_objects()
        return self._objects

    def parse_objects(self):
        objects = {}

        _round = lambda x: round(x, 3) if type(x) == float else x

        def process_object(obj):

            attr = dict((k, _round(v)) for k, v in obj.__dict__.items()
                if isinstance(v, (float, int, string_types))
                    and k[0] != "_")

            kind = re.sub(lt_pat, "", obj.__class__.__name__).lower()
            attr["object_type"] = kind
            attr["pageid"] = self.pageid

            if hasattr(obj, "get_text"):
                attr["text"] = obj.get_text()

            if attr.get("y0") != None:
                attr["top"] = self.layout.height - attr["y1"]
                attr["bottom"] = self.layout.height - attr["y0"]
                attr["doctop"] = self.initial_doctop + attr["top"]

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
        edges_clust = helpers.cluster_list(edges_uniq, tolerance=tolerance)
        edge_means = list(sorted(sum(c) / len(c) for c in edges_clust))

        return edge_means

    def extract_table(self,
        v="lines",
        h="lines",
        bbox=None,
        line_min_height=1,
        line_min_width=1,
        gutter_min_width=5,
        gutter_min_height=5,
        x_tolerance=0,
        y_tolerance=0):

        def use_strategy(param, name):
            if isinstance(param, (list, tuple)):
                return param
            if param in TABLE_STRATEGIES:
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
                    pass

                if param == "gutters":
                    if name == "v":
                        pos = sorted(set(c["x0"] for c in self.chars))
                        pos_gaps = ((p1, p2 - p1)
                            for p1, p2 in zip(pos, pos[1:]))
                        centers = [ g[0] + g[1]/2
                            for g in pos_gaps
                                if g[1] >= gutter_min_width ]
                        dividers = [ pos[0] ] + centers + [ pos[-1] + 1 ]
                        return dividers
                    if name == "h":
                        pos = sorted(set(c["top"] for c in self.chars))
                        pos_gaps = ((p1, p2 - p1)
                            for p1, p2 in zip(pos, pos[1:]))
                        centers = [ g[0] + g[1]/2
                            for g in pos_gaps
                                if g[1] >= gutter_min_height ]
                        dividers = [ pos[0] ] + centers + [ pos[-1] + 1 ]
                        return dividers

            msg = "`{0}` must be list/tuple of ints/floats or one of {1}"\
                .format(name, TABLE_STRATEGIES)
            raise Exception(msg)
        
        h = use_strategy(h, "h")
        v = use_strategy(v, "v")

        table = utils.extract_table(self.chars,
            v, h, x_tolerance=x_tolerance, y_tolerance=y_tolerance)

        return table

    def crop(self, bbox):
        return CroppedPage(self, bbox)

class CroppedPage(Page):
    def __init__(self, parent_page, bbox):
        self.parent_page = parent_page
        self.bbox = bbox

    @property
    def objects(self):
        if hasattr(self, "_objects"): return self._objects
        self._objects = utils.within_bbox(self.parent_page.objects, self.bbox,
            crop=True) 
        return self._objects
