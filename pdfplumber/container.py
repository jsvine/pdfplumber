import csv
import json
from io import StringIO
from itertools import chain
from typing import Any, Dict, List, Optional, Set, TextIO

from . import utils
from ._typing import T_obj, T_obj_list
from .convert import CSV_COLS_REQUIRED, CSV_COLS_TO_PREPEND, Serializer


class Container(object):
    cached_properties = ["_rect_edges", "_edges", "_objects"]

    @property
    def pages(self) -> Optional[List[Any]]:
        ...  # pragma: nocover

    @property
    def objects(self) -> Dict[str, T_obj_list]:
        ...  # pragma: nocover

    def to_dict(self, object_types: Optional[List[str]] = None) -> Dict[str, Any]:
        ...  # pragma: nocover

    def flush_cache(self, properties: Optional[List[str]] = None) -> None:
        props = self.cached_properties if properties is None else properties
        for p in props:
            if hasattr(self, p):
                delattr(self, p)

    @property
    def rects(self) -> T_obj_list:
        return self.objects.get("rect", [])

    @property
    def lines(self) -> T_obj_list:
        return self.objects.get("line", [])

    @property
    def curves(self) -> T_obj_list:
        return self.objects.get("curve", [])

    @property
    def images(self) -> T_obj_list:
        return self.objects.get("image", [])

    @property
    def chars(self) -> T_obj_list:
        return self.objects.get("char", [])

    @property
    def textboxverticals(self) -> T_obj_list:
        return self.objects.get("textboxvertical", [])

    @property
    def textboxhorizontals(self) -> T_obj_list:
        return self.objects.get("textboxhorizontal", [])

    @property
    def textlineverticals(self) -> T_obj_list:
        return self.objects.get("textlinevertical", [])

    @property
    def textlinehorizontals(self) -> T_obj_list:
        return self.objects.get("textlinehorizontal", [])

    @property
    def rect_edges(self) -> T_obj_list:
        if hasattr(self, "_rect_edges"):
            return self._rect_edges
        rect_edges_gen = (utils.rect_to_edges(r) for r in self.rects)
        self._rect_edges: T_obj_list = list(chain(*rect_edges_gen))
        return self._rect_edges

    @property
    def edges(self) -> T_obj_list:
        if hasattr(self, "_edges"):
            return self._edges
        line_edges = list(map(utils.line_to_edge, self.lines))
        self._edges: T_obj_list = self.rect_edges + line_edges
        return self._edges

    @property
    def horizontal_edges(self) -> T_obj_list:
        def test(x: T_obj) -> bool:
            return bool(x["orientation"] == "h")

        return list(filter(test, self.edges))

    @property
    def vertical_edges(self) -> T_obj_list:
        def test(x: T_obj) -> bool:
            return bool(x["orientation"] == "v")

        return list(filter(test, self.edges))

    def to_json(
        self,
        stream: Optional[TextIO] = None,
        object_types: Optional[List[str]] = None,
        include_attrs: Optional[List[str]] = None,
        exclude_attrs: Optional[List[str]] = None,
        precision: Optional[int] = None,
        indent: Optional[int] = None,
    ) -> Optional[str]:

        data = self.to_dict(object_types)

        serialized = Serializer(
            precision=precision,
            include_attrs=include_attrs,
            exclude_attrs=exclude_attrs,
        ).serialize(data)

        if stream is None:
            return json.dumps(serialized, indent=indent)
        else:
            json.dump(serialized, stream, indent=indent)
            return None

    def to_csv(
        self,
        stream: Optional[TextIO] = None,
        object_types: Optional[List[str]] = None,
        precision: Optional[int] = None,
        include_attrs: Optional[List[str]] = None,
        exclude_attrs: Optional[List[str]] = None,
    ) -> Optional[str]:
        if stream is None:
            stream = StringIO()
            to_string = True
        else:
            to_string = False

        if object_types is None:
            object_types = list(self.objects.keys()) + ["annot"]

        serialized = []
        fields: Set[str] = set()

        pages = [self] if self.pages is None else self.pages

        serializer = Serializer(
            precision=precision,
            include_attrs=include_attrs,
            exclude_attrs=exclude_attrs,
        )
        for page in pages:
            for t in object_types:
                objs = getattr(page, t + "s")
                if len(objs):
                    serialized += serializer.serialize(objs)
                    new_keys = [k for k, v in objs[0].items() if type(v) is not dict]
                    fields = fields.union(set(new_keys))

        non_req_cols = CSV_COLS_TO_PREPEND + list(
            sorted(set(fields) - set(CSV_COLS_REQUIRED + CSV_COLS_TO_PREPEND))
        )

        cols = CSV_COLS_REQUIRED + list(filter(serializer.attr_filter, non_req_cols))

        w = csv.DictWriter(stream, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(serialized)

        if to_string:
            stream.seek(0)
            return stream.read()
        else:
            return None
