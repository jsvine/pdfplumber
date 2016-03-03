from six import string_types
from six.moves import cStringIO

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams, LTChar, LTImage, LTPage
from pdfminer.converter import PDFPageAggregator

import re
lt_pat = re.compile(r"^LT")

class Container(object):
    @property
    def rects(self):
        return self.objects.get("rect", [])

    @property
    def lines(self):
        return self.objects.get("line", [])

    @property
    def images(self):
        return self.objects.get("image", [])

    @property
    def figures(self):
        return self.objects.get("figure", [])

    @property
    def chars(self):
        return self.objects.get("char", [])

    @property
    def annos(self):
        return self.objects.get("anno", [])

class Page(Container):
    def __init__(self, layout, initial_doctop=0):
        self.layout = layout
        self.width = layout.width
        self.height = layout.height
        self.pageid = layout.pageid
        self.initial_doctop = 0
        self.objects = self.parse_objects()

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

class PDF(Container):
    def __init__(self, file_or_buffer, pages=None, laparams=None):
        self.laparams = None if laparams == None else LAParams(**laparams)

        rsrcmgr = PDFResourceManager()
        self.doc = PDFDocument(PDFParser(file_or_buffer))
        self.device = PDFPageAggregator(rsrcmgr, laparams=self.laparams)
        self.interpreter = PDFPageInterpreter(rsrcmgr, self.device)

        self.pages = []

        page_iter = (p for i, p in enumerate(PDFPage.create_pages(self.doc))
            if pages == None or i+1 in pages)

        doctop = 0
        for page in page_iter:
            self.interpreter.process_page(page)
            layout = self.device.get_result()
            p = Page(layout, initial_doctop=doctop)
            self.pages.append(p)
            doctop += p.layout.height

    @property
    def objects(self):
        all_objects = {}
        for p in self.pages:
            for kind in p.objects.keys():
                all_objects[kind] = all_objects.get(kind, []) + p.objects[kind]
        return all_objects
