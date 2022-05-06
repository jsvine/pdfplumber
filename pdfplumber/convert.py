import base64
from typing import Any, Dict, List, Optional, Tuple

from pdfminer.psparser import PSLiteral

from .utils import decode_text

ENCODINGS_TO_TRY = [
    "utf-8",
    "latin-1",
    "utf-16",
    "utf-16le",
]


def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


class Serializer:
    def __init__(self, precision: Optional[int] = None):
        self.precision = precision

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
