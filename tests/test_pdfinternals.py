from io import BytesIO

import pytest

import pdfplumber
from pdfplumber.utils import decode_text


@pytest.mark.parametrize(
    "value, expected",
    [
        (b"\xef\xbb\xbfASCII", "ASCII"),
        (b"\xef\xbb\xbf" + "Café 日本語 😀".encode("utf-8"), "Café 日本語 😀"),
        (b"\xef\xbb\xbf", ""),
        (b"\xef\xbb\xbfleft\xffright", "leftright"),
        (b"\xef\xbb\xbftext\xe2\x82", "text"),
    ],
)
def test_decode_utf8_text_strings(value, expected):
    assert decode_text(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (b"ASCII", "ASCII"),
        (b"Caf\xe9", "Café"),
        (b"\xc3\xa9", "Ã©"),
        (b"\xef\xbbX", "ï»X"),
        (b"\xfe\xff" + "日本語".encode("utf-16be"), "日本語"),
        (b"\xfe\xff\x00A\x00", "A"),
        ("already Unicode Ω", "already Unicode Ω"),
    ],
)
def test_decode_legacy_text_strings(value, expected):
    assert decode_text(value) == expected


def test_utf8_document_metadata():
    title = "Café 日本語 😀"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200]" b" /Resources << >> >>",
        b"<< /Title <"
        + (b"\xef\xbb\xbf" + title.encode("utf-8")).hex().encode("ascii")
        + b"> /Author <FEFF0041007500740068006F0072> /Subject <436166E9> >>",
    ]
    stream = BytesIO()
    stream.write(b"%PDF-2.0\n")
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(stream.tell())
        stream.write(b"%d 0 obj\n" % number + obj + b"\nendobj\n")
    xref = stream.tell()
    stream.write(b"xref\n0 5\n0000000000 65535 f \n")
    for offset in offsets:
        stream.write(b"%010d 00000 n \n" % offset)
    stream.write(
        b"trailer\n<< /Size 5 /Root 1 0 R /Info 4 0 R >>\nstartxref\n"
        b"%d\n%%%%EOF\n" % xref
    )
    stream.seek(0)

    with pdfplumber.open(stream) as pdf:
        assert pdf.metadata == {"Title": title, "Author": "Author", "Subject": "Café"}
