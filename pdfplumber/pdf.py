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

class PDF(object):
    def __init__(self, file_or_buffer, pages=None, laparams=None):
        self.laparams = None if laparams == None else LAParams(**laparams)

        rsrcmgr = PDFResourceManager()
        self.doc = PDFDocument(PDFParser(file_or_buffer))
        self.device = PDFPageAggregator(rsrcmgr, laparams=self.laparams)
        self.interpreter = PDFPageInterpreter(rsrcmgr, self.device)

        self.pages = []
        page_iter = (p for i, p in enumerate(PDFPage.create_pages(self.doc))
            if pages == None or i+1 in pages)
        for page in page_iter:
            self.interpreter.process_page(page)
            layout = self.device.get_result()
            self.pages.append(layout)

        self.objects = self.parse()

    def parse(self):
        try:
            # pdfminer < 20131022
            _pages = self.doc.get_pages()
        except AttributeError:
            # pdfminer >= 20131022
            _pages = PDFPage.create_pages(self.doc)

        objects = {}

        def process_object(obj, page):
            _round = lambda x: round(x, 3) if type(x) == float else x

            attr = dict((k, _round(v)) for k, v in obj.__dict__.items()
                if isinstance(v, (float, int, string_types))
                    and k[0] != "_")

            kind = re.sub(lt_pat, "", obj.__class__.__name__).lower()
            attr["object_type"] = kind
            attr["pageid"] = page.pageid

            if hasattr(obj, "get_text"):
                attr["text"] = obj.get_text()

            if attr.get("y0") != None:
                page_index = self.pages.index(page)
                prev_h = sum(p.height for p in self.pages[:page_index])
                attr["top"] = _round(page.height - attr["y1"])
                attr["doctop"] = _round(prev_h + attr["top"])

            if objects.get(kind) == None:
                objects[kind] = []
            objects[kind].append(attr)

            if hasattr(obj, "_objs"):
                for child in obj._objs:
                    process_object(child, page)
        
        def process_page(page):
            for child in page._objs:
                process_object(child, page)

        for page in self.pages:
            process_page(page)

        return objects

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
