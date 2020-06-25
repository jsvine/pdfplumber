from .container import Container
from .page import Page
from .utils import decode_text

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.psparser import PSLiteral

class PDF(Container):
    cached_properties = Container.cached_properties + [ "_pages" ]

    def __init__(self,
        stream,
        pages = None,
        laparams = None,
        precision = 0.001,
        password = ""
    ):
        self.laparams = None if laparams == None else LAParams(**laparams)
        self.stream = stream
        self.pages_to_parse = pages
        self.precision = precision
        rsrcmgr = PDFResourceManager()
        self.doc = PDFDocument(PDFParser(stream), password = password)
        self.metadata = {}
        for info in self.doc.info:
            self.metadata.update(info)
        for k, v in self.metadata.items():
            if hasattr(v, "resolve"):
                v = v.resolve()
            if type(v) == list:
                self.metadata[k] = list(map(decode_text, v))
            elif isinstance(v, PSLiteral):
                self.metadata[k] = decode_text(v.name)
            elif isinstance(v, bool):
                self.metadata[k] = v
            else:
                self.metadata[k] = decode_text(v)
        self.device = PDFPageAggregator(rsrcmgr, laparams=self.laparams)
        self.interpreter = PDFPageInterpreter(rsrcmgr, self.device)

    @classmethod
    def open(cls, path, **kwargs):
        return cls(open(path, "rb"), **kwargs)

    def process_page(self, page):
        self.interpreter.process_page(page)
        return self.device.get_result()

    @property
    def pages(self):
        if hasattr(self, "_pages"): return self._pages

        doctop = 0
        pp = self.pages_to_parse
        self._pages = []
        for i, page in enumerate(PDFPage.create_pages(self.doc)):
            page_number = i+1
            if pp != None and page_number not in pp: continue
            p = Page(self, page, page_number=page_number, initial_doctop=doctop)
            self._pages.append(p)
            doctop += p.height
        return self._pages

    def close(self):
        self.stream.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.flush_cache()
        self.close()

    @property
    def objects(self):
        if hasattr(self, "_objects"): return self._objects
        all_objects = {}
        for p in self.pages:
            for kind in p.objects.keys():
                all_objects[kind] = all_objects.get(kind, []) + p.objects[kind]
        self._objects = all_objects
        return self._objects
