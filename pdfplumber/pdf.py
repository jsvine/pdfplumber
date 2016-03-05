from pdfplumber.container import Container
from pdfplumber.page import Page

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator

import atexit

class PDF(Container):
    cached_properties = Container.cached_properties + [ "_pages" ]

    def __init__(self, stream, pages=None, laparams=None):
        self.laparams = None if laparams == None else LAParams(**laparams)
        self.stream = stream
        self.pages_to_parse = pages
        rsrcmgr = PDFResourceManager()
        self.doc = PDFDocument(PDFParser(stream))
        self.metadata = {}
        for info in self.doc.info:
            self.metadata.update(info)
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
