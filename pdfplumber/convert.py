from .utils import decode_text
from decimal import Decimal, ROUND_HALF_UP
from pdfminer.pdftypes import PDFStream
from pdfminer.psparser import PSLiteral
import json
import csv
import base64
from io import StringIO

COLS_TO_PREPEND = [
    "object_type",
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

ENCODINGS_TO_TRY = [
    "utf-8",
    "latin-1",
    "utf-16",
    "utf-16le",
]


def to_b64(data_bytes):
    return base64.b64encode(data_bytes).decode("ascii")


def try_decode_bytes(obj):
    for e in ENCODINGS_TO_TRY:
        try:
            return obj.decode(e)
        except UnicodeDecodeError:  # pragma: no cover
            pass
    # If none of the decodings work, raise whatever error
    # decoding with utf-8 causes
    obj.decode(ENCODINGS_TO_TRY[0])  # pragma: no cover


serializers = {
    Decimal: lambda obj: float(obj.quantize(Decimal(".0001"), rounding=ROUND_HALF_UP)),
    list: lambda obj: list(serialize(x) for x in obj),
    tuple: lambda obj: tuple(serialize(x) for x in obj),
    dict: lambda obj: {k: serialize(v) for k, v in obj.items()},
    PDFStream: lambda obj: {"rawdata": to_b64(obj.rawdata)},
    PSLiteral: lambda obj: decode_text(obj.name),
    bytes: try_decode_bytes,
    bool: int,
}


def serialize(obj):
    if obj is None:
        return None

    t = type(obj)

    # Basic types don't need to be converted
    if t in (int, float, str):
        return obj

    # Use one of the custom converters above, if possible
    fn = serializers.get(t)
    if fn is not None:
        return fn(obj)

    # Otherwise, just use the string-representation
    else:
        return str(obj)


def to_json(container, stream=None, types=None, indent=None):
    if types is None:
        types = list(container.objects.keys()) + ["annot"]

    def page_to_dict(page):
        d = {
            "page_number": page.page_number,
            "initial_doctop": page.initial_doctop,
            "rotation": page.rotation,
            "cropbox": page.cropbox,
            "mediabox": page.mediabox,
            "bbox": page.bbox,
            "width": page.width,
            "height": page.height,
        }
        for t in types:
            d[t + "s"] = getattr(page, t + "s")
        return d

    if hasattr(container, "pages"):
        data = {
            "metadata": container.metadata,
            "pages": list(map(page_to_dict, container.pages)),
        }
    else:
        data = page_to_dict(container)

    serialized = serialize(data)

    if stream is None:
        return json.dumps(serialized, indent=indent)
    else:
        return json.dump(serialized, stream, indent=indent)


def to_csv(container, stream=None, types=None):
    if stream is None:
        stream = StringIO()
        to_string = True
    else:
        to_string = False

    if types is None:
        types = list(container.objects.keys()) + ["annot"]

    objs = []
    fields = set()

    pages = container.pages if hasattr(container, "pages") else [container]
    for page in pages:
        for t in types:
            new_objs = getattr(page, t + "s")
            if len(new_objs):
                objs += new_objs
                new_keys = [k for k, v in new_objs[0].items() if type(v) is not dict]
                fields = fields.union(set(new_keys))

    cols = COLS_TO_PREPEND + list(sorted(set(fields) - set(COLS_TO_PREPEND)))

    w = csv.DictWriter(stream, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(serialize(objs))
    if to_string:
        stream.seek(0)
        return stream.read()
