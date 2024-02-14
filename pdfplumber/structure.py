import logging
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple

from pdfminer.data_structures import NumberTree
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import PDFObjRef, resolve1
from pdfminer.psparser import PSLiteral

from .utils import decode_text

logger = logging.getLogger(__name__)


if TYPE_CHECKING:  # pragma: nocover
    from .page import Page
    from .pdf import PDF


@dataclass
class PDFStructElement:
    type: str
    revision: Optional[int]
    id: Optional[str]
    lang: Optional[str]
    alt_text: Optional[str]
    actual_text: Optional[str]
    title: Optional[str]
    page_number: Optional[int]
    attributes: Dict[str, Any] = field(default_factory=dict)
    mcids: List[int] = field(default_factory=list)
    children: List["PDFStructElement"] = field(default_factory=list)

    def __iter__(self) -> Iterator["PDFStructElement"]:
        return iter(self.children)

    def to_dict(self) -> Dict[str, Any]:
        """Return a compacted dict representation."""
        r = asdict(self)
        d = deque([r])
        while d:
            el = d.popleft()
            for k in list(el.keys()):
                if el[k] is None or el[k] == [] or el[k] == {}:
                    del el[k]
            if "children" in el:
                d.extend(el["children"])
        return r


class StructTreeMissing(ValueError):
    pass


class PDFStructTree:
    """Parse the structure tree of a PDF.

    The constructor takes a `pdfplumber.PDF` and optionally a
    `pdfplumber.Page`.  To avoid creating the entire tree for a large
    document it is recommended to provide a page.

    This class creates a representation of the portion of the
    structure tree that reaches marked content sections, either for a
    single page, or for the whole document.  Note that this is slightly
    different from the behaviour of other PDF libraries which will
    also include structure elements with no content.

    If the PDF has no structure, the constructor will raise
    `StructTreeMissing`.

    """

    page: Optional[PDFPage]

    def __init__(self, doc: "PDF", page: Optional["Page"] = None):
        self.doc = doc.doc
        if "StructTreeRoot" not in self.doc.catalog:
            raise StructTreeMissing("PDF has no structure")
        self.root = resolve1(self.doc.catalog["StructTreeRoot"])
        self.role_map = resolve1(self.root.get("RoleMap", {}))
        self.class_map = resolve1(self.root.get("ClassMap", {}))
        self.children: List[PDFStructElement] = []

        # If we have a specific page then we will work backwards from
        # its ParentTree - this is because structure elements could
        # span multiple pages, and the "Pg" attribute is *optional*,
        # so this is the approved way to get a page's structure...
        if page is not None:
            self.page = page.page_obj
            self.page_dict = None
            # ...EXCEPT that the ParentTree is sometimes missing, in which
            # case we fall back to the non-approved way.
            parent_tree_obj = self.root.get("ParentTree")
            if parent_tree_obj is None:
                self._parse_struct_tree()
            else:
                parent_tree = NumberTree(parent_tree_obj)
                # If there is no marked content in the structure tree for
                # this page (which can happen even when there is a
                # structure tree) then there is no `StructParents`.
                # Note however that if there are XObjects in a page,
                # *they* may have `StructParent` (not `StructParents`)
                if "StructParents" not in self.page.attrs:
                    return
                parent_id = self.page.attrs["StructParents"]
                # NumberTree should have a `get` method like it does in pdf.js...
                parent_array = resolve1(
                    next(array for num, array in parent_tree.values if num == parent_id)
                )
                self._parse_parent_tree(parent_array)
        else:
            self.page = None
            # Overhead of creating pages shouldn't be too bad we hope!
            self.page_dict = {
                page.page_obj.pageid: page.page_number for page in doc.pages
            }
            self._parse_struct_tree()

    def _make_attributes(
        self, obj: Dict[str, Any], revision: Optional[int]
    ) -> Dict[str, Any]:
        attr_obj_list = []
        for key in "C", "A":
            if key not in obj:
                continue
            attr_obj = resolve1(obj[key])
            # It could be a list of attribute objects (why?)
            if isinstance(attr_obj, list):
                attr_obj_list.extend(attr_obj)
            else:
                attr_obj_list.append(attr_obj)
        attr_objs = []
        prev_obj = None
        for aref in attr_obj_list:
            # If we find a revision number, which might "follow the
            # revision object" (the spec is not clear about what this
            # should look like but it implies they are simply adjacent
            # in a flat array), then use it to decide whether to take
            # the previous object...
            if isinstance(aref, int):
                if aref == revision and prev_obj is not None:
                    attr_objs.append(prev_obj)
                prev_obj = None
            else:
                if prev_obj is not None:
                    attr_objs.append(prev_obj)
                prev_obj = resolve1(aref)
        if prev_obj is not None:
            attr_objs.append(prev_obj)
        # Now merge all the attribute objects in the collected to a
        # single set (again, the spec doesn't really explain this but
        # does say that attributes in /A supersede those in /C)
        attr = {}
        for obj in attr_objs:
            if isinstance(obj, PSLiteral):
                key = decode_text(obj.name)
                if key not in self.class_map:
                    logger.warning("Unknown attribute class %s", key)
                    continue
                obj = self.class_map[key]
            for k, v in obj.items():
                if isinstance(v, PSLiteral):
                    attr[k] = decode_text(v.name)
                else:
                    attr[k] = obj[k]
        return attr

    def _make_element(self, obj: Any) -> Tuple[Optional[PDFStructElement], List[Any]]:
        # We hopefully caught these earlier
        assert "MCID" not in obj, "Uncaught MCR: %s" % obj
        assert "Obj" not in obj, "Uncaught OBJR: %s" % obj
        # Get page number if necessary
        page_number = None
        if self.page_dict is not None and "Pg" in obj:
            page_objid = obj["Pg"].objid
            assert page_objid in self.page_dict, "Object on unparsed page: %s" % obj
            page_number = self.page_dict[page_objid]
        obj_tag = ""
        if "S" in obj:
            obj_tag = decode_text(obj["S"].name)
            if obj_tag in self.role_map:
                obj_tag = decode_text(self.role_map[obj_tag].name)
        children = resolve1(obj["K"]) if "K" in obj else []
        if isinstance(children, int):  # ugh... isinstance...
            children = [children]
        elif isinstance(children, dict):  # a single object.. ugh...
            children = [obj["K"]]
        revision = obj.get("R")
        attributes = self._make_attributes(obj, revision)
        element_id = decode_text(obj["ID"]) if "ID" in obj else None
        title = decode_text(obj["T"]) if "T" in obj else None
        lang = decode_text(obj["Lang"]) if "Lang" in obj else None
        alt_text = decode_text(obj["Alt"]) if "Alt" in obj else None
        actual_text = decode_text(obj["ActualText"]) if "ActualText" in obj else None
        element = PDFStructElement(
            type=obj_tag,
            id=element_id,
            page_number=page_number,
            revision=revision,
            lang=lang,
            title=title,
            alt_text=alt_text,
            actual_text=actual_text,
            attributes=attributes,
        )
        return element, children

    def _parse_parent_tree(self, parent_array: List[Any]) -> None:
        """Populate the structure tree using the leaves of the parent tree for
        a given page."""
        # First walk backwards from the leaves to the root, tracking references
        d = deque(parent_array)
        s = {}
        found_root = False
        while d:
            ref = d.popleft()
            # In the case where an MCID is not associated with any
            # structure, there will be a "null" in the parent tree.
            if ref == PDFParser.KEYWORD_NULL:
                continue
            if repr(ref) in s:
                continue
            obj = resolve1(ref)
            # This is required! It's in the spec!
            if "Type" in obj and decode_text(obj["Type"].name) == "StructTreeRoot":
                found_root = True
            else:
                # We hope that these are actual elements and not
                # references or marked-content sections...
                element, children = self._make_element(obj)
                # We have no page tree so we assume this page was parsed
                assert element is not None
                s[repr(ref)] = element, children
                d.append(obj["P"])
        # If we didn't reach the root something is quite wrong!
        assert found_root
        self._resolve_children(s)

    def on_parsed_page(self, obj: Dict[str, Any]) -> bool:
        if "Pg" not in obj:
            return True
        page_objid = obj["Pg"].objid
        if self.page_dict is not None:
            return page_objid in self.page_dict
        if self.page is not None:
            # We have to do this to satisfy mypy
            if page_objid != self.page.pageid:
                return False
        return True

    def _parse_struct_tree(self) -> None:
        """Populate the structure tree starting from the root, skipping
        unparsed pages and empty elements."""
        root = resolve1(self.root["K"])

        # It could just be a single object ... it's in the spec (argh)
        if isinstance(root, dict):
            root = [self.root["K"]]
        d = deque(root)
        s = {}
        while d:
            ref = d.popleft()
            # In case the tree is actually a DAG and not a tree...
            if repr(ref) in s:  # pragma: nocover (shouldn't happen)
                continue
            obj = resolve1(ref)
            # Deref top-level OBJR skipping refs to unparsed pages
            if isinstance(obj, dict) and "Obj" in obj:
                if not self.on_parsed_page(obj):
                    continue
                ref = obj["Obj"]
                obj = resolve1(ref)
            element, children = self._make_element(obj)
            # Similar to above, delay resolving the children to avoid
            # tree-recursion.
            s[repr(ref)] = element, children
            for child in children:
                obj = resolve1(child)
                if isinstance(obj, dict):
                    if not self.on_parsed_page(obj):
                        continue
                    if "Obj" in obj:
                        child = obj["Obj"]
                    elif "MCID" in obj:
                        continue
                if isinstance(child, PDFObjRef):
                    d.append(child)

        # Traverse depth-first, removing empty elements (unsure how to
        # do this non-recursively)
        def prune(elements: List[Any]) -> List[Any]:
            next_elements = []
            for ref in elements:
                obj = resolve1(ref)
                if isinstance(ref, int):
                    next_elements.append(ref)
                    continue
                elif isinstance(obj, dict):
                    if not self.on_parsed_page(obj):
                        continue
                    if "MCID" in obj:
                        next_elements.append(obj["MCID"])
                        continue
                    elif "Obj" in obj:
                        ref = obj["Obj"]
                element, children = s[repr(ref)]
                children = prune(children)
                # See assertions below
                if element is None or not children:
                    del s[repr(ref)]
                else:
                    s[repr(ref)] = element, children
                    next_elements.append(ref)
            return next_elements

        prune(root)
        self._resolve_children(s)

    def _resolve_children(self, seen: Dict[str, Any]) -> None:
        """Resolve children starting from the tree root based on references we
        saw when traversing the structure tree.
        """
        root = resolve1(self.root["K"])
        # It could just be a single object ... it's in the spec (argh)
        if isinstance(root, dict):
            root = [self.root["K"]]
        self.children = []
        # Create top-level self.children
        parsed_root = []
        for ref in root:
            obj = resolve1(ref)
            if isinstance(obj, dict) and "Obj" in obj:
                if not self.on_parsed_page(obj):
                    continue
                ref = obj["Obj"]
            if repr(ref) in seen:
                parsed_root.append(ref)
        d = deque(parsed_root)
        while d:
            ref = d.popleft()
            element, children = seen[repr(ref)]
            assert element is not None, "Unparsed element"
            for child in children:
                obj = resolve1(child)
                if isinstance(obj, int):
                    element.mcids.append(obj)
                elif isinstance(obj, dict):
                    # Skip out-of-page MCIDS and OBJRs
                    if not self.on_parsed_page(obj):
                        continue
                    if "MCID" in obj:
                        element.mcids.append(obj["MCID"])
                    elif "Obj" in obj:
                        child = obj["Obj"]
                # NOTE: if, not elif, in case of OBJR above
                if isinstance(child, PDFObjRef):
                    child_element, _ = seen.get(repr(child), (None, None))
                    if child_element is not None:
                        element.children.append(child_element)
                        d.append(child)
        self.children = [seen[repr(ref)][0] for ref in parsed_root]

    def __iter__(self) -> Iterator[PDFStructElement]:
        return iter(self.children)
