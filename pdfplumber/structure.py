from collections import deque
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterator, Optional, TYPE_CHECKING

from playa.structtree import StructElement, StructTree

if TYPE_CHECKING:  # pragma: nocover
    from .pdf import PDF
    from .page import Page


class StructTreeMissing(ValueError):
    pass


class PDFStructElement(StructElement):
    """PDF Logical Structure Element"""

    # When PLAYA changes its API, wrap it here...


class PDFStructTree(StructTree):
    """PDF Logical Structure Tree"""

    def __init__(self, doc: "PDF", page: Optional["Page"] = None):
        self.doc = doc.doc
        try:
            if page is not None:
                pages = [page.page_obj]
            else:
                pages = None
            super().__init__(self.doc, pages)
        except KeyError:
            raise StructTreeMissing("PDF has no structure")

    # May wish to wrap __iter__, find, find_all in the future


def structure_dict(top: StructElement) -> Dict[str, Any]:
    """Return a compacted dict representation of PDF structure."""
    r = asdict(top)
    # Prune empty values (does not matter in which order)
    d = deque([r])
    while d:
        el = d.popleft()
        for k in list(el.keys()):
            if el[k] is None or el[k] == [] or el[k] == {}:
                del el[k]
        if "page_idx" in el:
            el["page_number"] = el["page_idx"] + 1
            del el["page_idx"]
        if "children" in el:
            d.extend(el["children"])
    return r
