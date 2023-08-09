import ctypes
from io import BufferedReader, BytesIO
from typing import TYPE_CHECKING, Callable, Iterator, Optional, Union

import pypdfium2  # type: ignore
import pypdfium2.raw as pdfium_c  # type: ignore

from ._typing import T_obj

if TYPE_CHECKING:
    fpdf_structelement_t = ctypes._Pointer[pdfium_c.fpdf_structelement_t__]
    fpdf_structtree_t = ctypes._Pointer[pdfium_c.fpdf_structtree_t__]
    c_char_array = ctypes.Array[ctypes.c_char]
else:
    fpdf_structelement_t = ctypes._Pointer
    fpdf_structtree_t = ctypes._Pointer
    c_char_array = ctypes.Array


class PdfStructElement:
    def __init__(self, raw: fpdf_structelement_t):
        self.raw = raw

    @property
    def children(self) -> Iterator["PdfStructElement"]:
        n_children = pdfium_c.FPDF_StructElement_CountChildren(self.raw)
        for idx in range(n_children):
            child = PdfStructElement(
                pdfium_c.FPDF_StructElement_GetChildAtIndex(self.raw, idx)
            )
            if child.type:
                yield child

    def string_accessor(
        self,
        pdffunc: Callable[
            [
                fpdf_structelement_t,
                Optional[c_char_array],
                int,
            ],
            int,
        ],
    ) -> str:
        n_bytes = pdffunc(self.raw, None, 0)
        buffer = ctypes.create_string_buffer(n_bytes)
        pdffunc(self.raw, buffer, n_bytes)
        return buffer.raw[: n_bytes - 2].decode("utf-16-le")

    @property
    def id(self) -> str:
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetID)

    @property
    def lang(self) -> str:
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetLang)

    @property
    def title(self) -> str:
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetTitle)

    @property
    def type(self) -> str:
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetType)

    @property
    def alt_text(self) -> str:
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetAltText)

    @property
    def actual_text(self) -> str:
        return self.string_accessor(pdfium_c.FPDF_StructElement_GetActualText)

    @property
    def mcid(self) -> Optional[int]:
        mcid: int = pdfium_c.FPDF_StructElement_GetMarkedContentID(self.raw)
        if mcid == -1:
            return None
        else:
            return mcid

    @property
    def mcids(self) -> Iterator[int]:
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

    def to_dict(self) -> T_obj:
        eldict: T_obj = {}
        if self.id:
            eldict["id"] = self.id  # pragma: nocover
        if self.lang:
            eldict["lang"] = self.lang
        if self.title:
            eldict["title"] = self.title  # pragma: nocover
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
    def __init__(self, raw: fpdf_structtree_t):
        self.raw = raw

    @classmethod
    def from_page(self, page: pypdfium2.PdfPage) -> "PdfStructTree":
        raw = pdfium_c.FPDF_StructTree_GetForPage(page)
        return PdfStructTree(raw)

    @property
    def children(self) -> Iterator[PdfStructElement]:
        n_children = pdfium_c.FPDF_StructTree_CountChildren(self.raw)
        for idx in range(n_children):
            child = PdfStructElement(
                pdfium_c.FPDF_StructTree_GetChildAtIndex(self.raw, idx)
            )
            if child.type:
                yield child


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
    pdf = pypdfium2.PdfDocument(src)
    return PdfStructTree.from_page(pdf[page_ix])
