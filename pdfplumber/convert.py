import base64
from typing import Any, Callable, Dict, List, Optional, Tuple

from pdfminer.psparser import PSLiteral

from .utils import decode_text

ENCODINGS_TO_TRY = [
    "utf-8",
    "latin-1",
    "utf-16",
    "utf-16le",
]

CSV_COLS_REQUIRED = [
    "object_type",
]

CSV_COLS_TO_PREPEND = [
    "page_number",
    "x0",
    "x1",
    "y0",
    "y1",
    "doctop",
    "top",
    "bottom",
    "width",
    "height",
]


def get_attr_filter(
    include_attrs: Optional[List[str]] = None, exclude_attrs: Optional[List[str]] = None
) -> Callable[[str], bool]:
    if include_attrs is not None and exclude_attrs is not None:
        raise ValueError(
            "Cannot specify `include_attrs` and `exclude_attrs` at the same time."
        )

    elif include_attrs is not None:
        incl = set(CSV_COLS_REQUIRED + include_attrs)
        return lambda attr: attr in incl

    elif exclude_attrs is not None:
        nonexcludable = set(exclude_attrs).intersection(set(CSV_COLS_REQUIRED))
        if len(nonexcludable):
            raise ValueError(
                f"Cannot exclude these required properties: {list(nonexcludable)}"
            )
        excl = set(exclude_attrs)
        return lambda attr: attr not in excl

    else:
        return lambda attr: True


def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


class Serializer:
    def __init__(
        self,
        precision: Optional[int] = None,
        include_attrs: Optional[List[str]] = None,
        exclude_attrs: Optional[List[str]] = None,
    ):

        self.precision = precision
        self.attr_filter = get_attr_filter(
            include_attrs=include_attrs, exclude_attrs=exclude_attrs
        )

    def serialize(self, obj: Any) -> Any:
        if obj is None:
            return None

        t = type(obj)

        # Basic types don't need to be converted
        if t in (int, str):
            return obj

        # Use one of the custom converters, if possible
        fn = getattr(self, f"do_{t.__name__}", None)
        if fn is not None:
            return fn(obj)

        # Otherwise, just use the string-representation
        else:
            return str(obj)

    def do_float(self, x: float) -> float:
        return x if self.precision is None else round(x, self.precision)

    def do_bool(self, x: bool) -> int:
        return int(x)

    def do_list(self, obj: List[Any]) -> List[Any]:
        return list(self.serialize(x) for x in obj)

    def do_tuple(self, obj: Tuple[Any, ...]) -> Tuple[Any, ...]:
        return tuple(self.serialize(x) for x in obj)

    def do_dict(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        if "object_type" in obj.keys():
            return {k: self.serialize(v) for k, v in obj.items() if self.attr_filter(k)}
        else:
            return {k: self.serialize(v) for k, v in obj.items()}

    def do_PDFStream(self, obj: Any) -> Dict[str, str]:
        return {"rawdata": to_b64(obj.rawdata)}

    def do_PSLiteral(self, obj: PSLiteral) -> str:
        return decode_text(obj.name)

    def do_bytes(self, obj: bytes) -> Optional[str]:
        for e in ENCODINGS_TO_TRY:
            try:
                return obj.decode(e)
            except UnicodeDecodeError:  # pragma: no cover
                return None
        # If none of the decodings work, raise whatever error
        # decoding with utf-8 causes
        obj.decode(ENCODINGS_TO_TRY[0])  # pragma: no cover
        return None  # pragma: no cover
