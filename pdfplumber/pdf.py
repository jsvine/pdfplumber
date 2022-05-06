import itertools
import logging
import pathlib
from io import BufferedReader
from types import TracebackType
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.psparser import PSException

from ._typing import T_num, T_obj_list
from .container import Container
from .page import Page
from .utils import resolve_and_decode

logger = logging.getLogger(__name__)


class PDF(Container):
    cached_properties: List[str] = Container.cached_properties + ["_pages"]

    def __init__(
        self,
        stream: BufferedReader,
        stream_is_external: bool = False,
        pages: Optional[Union[List[int], Tuple[int]]] = None,
        laparams: Optional[Dict[str, Any]] = None,
        password: str = "",
        strict_metadata: bool = False,
    ):
        self.stream = stream
        self.stream_is_external = stream_is_external
        self.pages_to_parse = pages
        self.laparams = None if laparams is None else LAParams(**laparams)

        self.doc = PDFDocument(PDFParser(stream), password=password)
        self.rsrcmgr = PDFResourceManager()
        self.metadata = {}

        for info in self.doc.info:
            self.metadata.update(info)
        for k, v in self.metadata.items():
            try:
                self.metadata[k] = resolve_and_decode(v)
            except Exception as e:  # pragma: nocover
                if strict_metadata:
                    # Raise an exception since unable to resolve the metadata value.
                    raise
                # This metadata value could not be parsed. Instead of failing the PDF
                # read, treat it as a warning only if `strict_metadata=False`.
                logger.warning(
                    f'[WARNING] Metadata key "{k}" could not be parsed due to '
                    f"exception: {str(e)}"
                )

    @classmethod
    def open(
        cls,
        path_or_fp: Union[str, pathlib.Path, BufferedReader],
        pages: Optional[Union[List[int], Tuple[int]]] = None,
        laparams: Optional[Dict[str, Any]] = None,
        password: str = "",
        strict_metadata: bool = False,
    ) -> "PDF":

        if isinstance(path_or_fp, (str, pathlib.Path)):
            stream = open(path_or_fp, "rb")
            stream_is_external = False
        else:
            stream = path_or_fp
            stream_is_external = True

        try:
            return cls(
                stream,
                pages=pages,
                laparams=laparams,
                password=password,
                strict_metadata=strict_metadata,
                stream_is_external=stream_is_external,
            )

        except PSException:
            if not stream_is_external:
                stream.close()
            raise

    def close(self) -> None:
        self.flush_cache()
        if not self.stream_is_external:
            self.stream.close()

    def __enter__(self) -> "PDF":
        return self

    def __exit__(
        self,
        t: Optional[Type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()

    @property
    def pages(self) -> List[Page]:
        if hasattr(self, "_pages"):
            return self._pages

        doctop: T_num = 0
        pp = self.pages_to_parse
        self._pages: List[Page] = []
        for i, page in enumerate(PDFPage.create_pages(self.doc)):
            page_number = i + 1
            if pp is not None and page_number not in pp:
                continue
            p = Page(self, page, page_number=page_number, initial_doctop=doctop)
            self._pages.append(p)
            doctop += p.height
        return self._pages

    @property
    def objects(self) -> Dict[str, T_obj_list]:
        if hasattr(self, "_objects"):
            return self._objects
        all_objects: Dict[str, T_obj_list] = {}
        for p in self.pages:
            for kind in p.objects.keys():
                all_objects[kind] = all_objects.get(kind, []) + p.objects[kind]
        self._objects: Dict[str, T_obj_list] = all_objects
        return self._objects

    @property
    def annots(self) -> List[Dict[str, Any]]:
        gen = (p.annots for p in self.pages)
        return list(itertools.chain(*gen))

    @property
    def hyperlinks(self) -> List[Dict[str, Any]]:
        gen = (p.hyperlinks for p in self.pages)
        return list(itertools.chain(*gen))

    def to_dict(self, object_types: Optional[List[str]] = None) -> Dict[str, Any]:
        return {
            "metadata": self.metadata,
            "pages": [page.to_dict(object_types) for page in self.pages],
        }
