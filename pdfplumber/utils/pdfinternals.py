from typing import Any, List, Optional, Union

from pdfminer.pdftypes import PDFObjRef
from pdfminer.psparser import PSLiteral
from pdfminer.utils import PDFDocEncoding


def decode_text(s: Union[bytes, str]) -> str:
    """
    Decodes a PDFDocEncoding string to Unicode.
    Adds py3 compatibility to pdfminer's version.
    """
    if isinstance(s, bytes) and s.startswith(b"\xfe\xff"):
        return str(s[2:], "utf-16be", "ignore")
    ords = (ord(c) if isinstance(c, str) else c for c in s)
    return "".join(PDFDocEncoding[o] for o in ords)


def resolve_and_decode(obj: Any) -> Any:
    """Recursively resolve the metadata values."""
    if hasattr(obj, "resolve"):
        obj = obj.resolve()
    if isinstance(obj, list):
        return list(map(resolve_and_decode, obj))
    elif isinstance(obj, PSLiteral):
        return decode_text(obj.name)
    elif isinstance(obj, (str, bytes)):
        return decode_text(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = resolve_and_decode(v)
        return obj

    return obj


def decode_psl_list(_list: List[Union[PSLiteral, str]]) -> List[str]:
    return [
        decode_text(value.name) if isinstance(value, PSLiteral) else value
        for value in _list
    ]


def resolve(x: Any) -> Any:
    if isinstance(x, PDFObjRef):
        return x.resolve()
    else:
        return x


def get_dict_type(d: Any) -> Optional[str]:
    if not isinstance(d, dict):
        return None
    t = d.get("Type")
    if isinstance(t, PSLiteral):
        return decode_text(t.name)
    else:
        return t


def resolve_all(x: Any) -> Any:
    """
    Recursively resolves the given object and all the internals.
    """
    if isinstance(x, PDFObjRef):
        resolved = x.resolve()

        # Avoid infinite recursion
        if get_dict_type(resolved) == "Page":
            return x

        return resolve_all(resolved)
    elif isinstance(x, (list, tuple)):
        return type(x)(resolve_all(v) for v in x)
    elif isinstance(x, dict):
        exceptions = ["Parent"] if get_dict_type(x) == "Annot" else []
        return {k: v if k in exceptions else resolve_all(v) for k, v in x.items()}
    else:
        return x
