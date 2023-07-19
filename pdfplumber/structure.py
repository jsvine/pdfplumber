import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
import ctypes
import json
from typing import Union, Optional
from io import BufferedReader, BytesIO


class PdfStructAttr:
    def __init__(self, raw):
        self.raw = raw


class PdfStructElement:
    def __init__(self, raw):
        self.raw = raw

    @property
    def children(self):
        n_children = pdfium_c.FPDF_StructElement_CountChildren(self.raw)
        for idx in range(n_children):
            child = pdfium_c.FPDF_StructElement_GetChildAtIndex(self.raw, idx)
            yield PdfStructElement(child)

    def string_accessor(self, pdffunc):
        n_bytes = pdffunc(self.raw, None, 0)
        buffer = ctypes.create_string_buffer(n_bytes)
        pdfium_c.FPDF_StructElement_GetType(self.raw, buffer, n_bytes)
        return buffer.raw[: n_bytes - 2].decode("utf-16-le")

    @property
    def id(self):
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetID)

    @property
    def lang(self):
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetLang)

    @property
    def title(self):
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetTitle)

    @property
    def type(self):
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetType)

    @property
    def alt_text(self):
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetAltText)

    @property
    def actual_text(self):
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetActualText)

    @property
    def mcid(self):
        mcid = pdfium_c.FPDF_StructElement_GetMarkedContentID(self.raw)
        if mcid == -1:
            return None
        else:
            return mcid

    @property
    def mcids(self):
        mcid_count = pdfium_c.FPDF_StructElement_GetMarkedContentIdCount(self.raw)
        if mcid_count == -1:
            return
        else:
            for idx in range(mcid_count):
                mcid = pdfium_c.FPDF_StructElement_GetMarkedContentIdAtIndex(
                    self.raw, idx
                )
                if mcid != -1:
                    yield mcid

    @property
    def attrs(self):
        attr_count = pdfium_c.FPDF_StructElement_GetAttributeCount(self.raw)
        for idx in range(attr_count):
            yield PdfStructAttr(
                pdfium_c.FPDF_StructElement_GetAttributeAtIndex(self.raw, idx)
            )

    def to_dict(self):
        eldict = {}
        if self.id:
            eldict["id"] = self.id
        if self.lang:
            eldict["lang"] = self.lang
        if self.title:
            eldict["title"] = self.title
        if self.type:
            eldict["type"] = self.type
        if self.alt_text:
            eldict["alt_text"] = self.alt_text
        if self.actual_text:
            eldict["actual_text"] = self.actual_text
        if self.mcid:
            eldict["mcids"] = [self.mcid]
        else:
            mcids = list(self.mcids)
            if mcids:
                eldict["mcids"] = mcids
        children = []
        for child in self.children:
            if child.type:
                children.append(child.to_dict())
        if children:
            eldict["children"] = children
        return eldict


class PdfStructTree:
    def __init__(self, raw):
        self.raw = raw

    @classmethod
    def from_page(self, page):
        raw = pdfium_c.FPDF_StructTree_GetForPage(page)
        return PdfStructTree(raw)

    @property
    def children(self):
        n_children = pdfium_c.FPDF_StructTree_CountChildren(self.raw)
        for idx in range(n_children):
            yield PdfStructElement(
                pdfium_c.FPDF_StructTree_GetChildAtIndex(self.raw, idx)
            )


def get_page_structure(
    stream: Union[BufferedReader, BytesIO],
    page_ix: int,
    password: Optional[str] = None,
) -> PdfStructTree:
    # If we are working with a file object saved to disk
    if hasattr(stream, "name"):
        src = stream.name
    # If we instead are working with a BytesIO stream
    else:
        stream.seek(0)
        src = stream
    pdf = pdfium.PdfDocument(src)
    return PdfStructTree.from_page(pdf[page_ix])
