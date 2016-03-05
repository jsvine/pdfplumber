from six import string_types
from six.moves import cStringIO

from pdfplumber.container import Container

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams, LTChar, LTImage, LTPage
from pdfminer.converter import PDFPageAggregator

import re
lt_pat = re.compile(r"^LT")

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
import atexit

class PDF(Container):
    def __init__(self, file_or_buffer, pages=None, laparams=None):
        self.laparams = None if laparams == None else LAParams(**laparams)

    def __init__(self, stream, pages=None, laparams=None):
        self.laparams = None if laparams == None else LAParams(**laparams)
        self.stream = stream
        self.pages_to_parse = pages
        rsrcmgr = PDFResourceManager()
        self.doc = PDFDocument(PDFParser(stream))
        self.device = PDFPageAggregator(rsrcmgr, laparams=self.laparams)
        self.interpreter = PDFPageInterpreter(rsrcmgr, self.device)
        atexit.register(self.close)

    @property
    def pages(self):
        if hasattr(self, "_pages"): return self._pages

        def process_page(page):
            self.interpreter.process_page(page)
            return self.device.get_result()

        doctop = 0
        pp = self.pages_to_parse
        self._pages = []
        for i, page in enumerate(PDFPage.create_pages(self.doc)):
            if pp != None and i+1 not in pp: continue
            p = Page(page, process_page, initial_doctop=doctop)
            self._pages.append(p)
            doctop += p.height
        return self._pages

    def close(self):
        self.stream.close()

    @property
    def objects(self):
        if hasattr(self, "_objects"): return self._objects
        all_objects = {}
        for p in self.pages:
            for kind in p.objects.keys():
                all_objects[kind] = all_objects.get(kind, []) + p.objects[kind]
        self._objects = all_objects
        return self._objects
