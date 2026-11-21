import io

import pytest
from PIL import ImageChops

import pdfplumber


def fixture(rect, rotation, origin=(0, 0)):
    ox, oy = origin
    rect = tuple(v + (ox if i % 2 == 0 else oy) for i, v in enumerate(rect))
    x0, x1 = sorted((rect[0], rect[2]))
    y0, y1 = sorted((rect[1], rect[3]))
    content = f"0 1 0 rg {x0} {y0} {x1 - x0} {y1 - y0} re f".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [{ox} {oy} {ox + 300} {oy + 400}] "
            f"/Rotate {rotation} /Resources << >> /Annots [4 0 R] "
            "/Contents 5 0 R >>"
        ).encode(),
        (
            f'<< /Type /Annot /Subtype /Link /Rect [{" ".join(map(str, rect))}] '
            "/A << /S /URI /URI (https://example.invalid/synthetic) >> >>"
        ).encode(),
        (f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream"),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(out)
    out.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(out)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize(
    "rect",
    [
        (50, 100, 150, 130),
        (150, 100, 50, 130),
        (50, 130, 150, 100),
        (150, 130, 50, 100),
    ],
)
def test_rotated_cropped_hyperlinks(rotation, rect):
    with pdfplumber.open(io.BytesIO(fixture(rect, rotation))) as pdf:
        page = pdf.pages[0]
        original = page.hyperlinks[0]
        bbox = pdfplumber.utils.obj_to_bbox(original)
        assert original["width"] > 0
        assert original["height"] > 0
        assert original["data"]["Rect"] == list(rect)
        for parent in [page, page.crop(page.bbox)]:
            for cropped in [parent.crop(bbox), parent.within_bbox(bbox)]:
                assert len(cropped.hyperlinks) == 1
                actual = cropped.hyperlinks[0]
                assert pdfplumber.utils.obj_to_bbox(actual) == bbox
                assert actual["uri"] == original["uri"]
                nested = cropped.crop(cropped.bbox)
                assert len(nested.hyperlinks) == 1
                assert pdfplumber.utils.obj_to_bbox(nested.hyperlinks[0]) == bbox
        assert page.outside_bbox(bbox).hyperlinks == []


@pytest.mark.parametrize("origin", [(20, 30), (-40, -70), (25, -30)])
@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize(
    "rect",
    [
        (50, 100, 150, 130),
        (150, 100, 50, 130),
        (50, 130, 150, 100),
        (150, 130, 50, 100),
    ],
)
def test_nonzero_origin_hyperlinks(origin, rotation, rect):
    with pdfplumber.open(io.BytesIO(fixture(rect, rotation, origin))) as pdf:
        page = pdf.pages[0]
        # The visible rectangle is parsed independently through pdfminer.
        bbox = pdfplumber.utils.obj_to_bbox(page.rects[0])
        original = page.hyperlinks[0]
        raw_rect = [value + origin[i % 2] for i, value in enumerate(rect)]
        assert original["data"]["Rect"] == raw_rect
        assert pdfplumber.utils.obj_to_bbox(original) == bbox
        relative_bbox = (
            bbox[0] - page.bbox[0],
            bbox[1] - page.bbox[1],
            bbox[2] - page.bbox[0],
            bbox[3] - page.bbox[1],
        )
        for parent in [page, page.crop(page.bbox)]:
            for cropped in [
                parent.crop(bbox),
                parent.within_bbox(bbox),
                parent.crop(relative_bbox, relative=True),
                parent.within_bbox(relative_bbox, relative=True),
            ]:
                assert len(cropped.hyperlinks) == 1
                actual = cropped.hyperlinks[0]
                assert pdfplumber.utils.obj_to_bbox(actual) == bbox
                assert actual["uri"] == original["uri"]
                assert actual["data"]["Rect"] == raw_rect
                nested = cropped.crop(
                    (0, 0, cropped.width, cropped.height), relative=True
                )
                assert len(nested.hyperlinks) == 1
                assert pdfplumber.utils.obj_to_bbox(nested.hyperlinks[0]) == bbox
        half = (bbox[0], bbox[1], (bbox[0] + bbox[2]) / 2, bbox[3])
        clipped = page.crop(half).hyperlinks
        assert len(clipped) == 1
        assert pdfplumber.utils.obj_to_bbox(clipped[0]) == half
        assert clipped[0]["uri"] == original["uri"]
        assert clipped[0]["data"]["Rect"] == raw_rect
        assert page.within_bbox(half).hyperlinks == []
        assert page.outside_bbox(bbox).hyperlinks == []


@pytest.mark.parametrize("origin", [(20, 30), (-40, -70), (25, -30)])
@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_nonzero_origin_hyperlink_rendering(origin, rotation):
    with pdfplumber.open(
        io.BytesIO(fixture((50, 100, 150, 130), rotation, origin))
    ) as pdf:
        page = pdf.pages[0]
        bbox = pdfplumber.utils.obj_to_bbox(page.rects[0])
        padded = (bbox[0] - 3, bbox[1] - 3, bbox[2] + 3, bbox[3] + 3)
        cropped = page.crop(padded)
        assert len(cropped.hyperlinks) == 1
        assert pdfplumber.utils.obj_to_bbox(cropped.hyperlinks[0]) == bbox
        image = cropped.to_image(resolution=144).original
        # PDFium independently renders the content stream. The link bbox must
        # cover the green pixels, with only the requested white padding.
        red, green_channel, blue = image.split()
        mask = ImageChops.subtract(green_channel, ImageChops.lighter(red, blue))
        assert mask.getbbox() == (6, 6, image.width - 6, image.height - 6)
        assert mask.histogram()[255] == 12000
        blank = (
            page.bbox[0] + 5,
            page.bbox[1] + 5,
            page.bbox[0] + 15,
            page.bbox[1] + 15,
        )
        assert page.crop(blank).hyperlinks == []
        assert page.within_bbox(blank).hyperlinks == []
        assert page.crop(blank).to_image().original.getextrema() == (
            (255, 255),
            (255, 255),
            (255, 255),
        )


def test_unrotated_fractional_origin_hyperlinks():
    with pdfplumber.open(
        io.BytesIO(fixture((0.3, 0.4, 10.3, 20.4), 0, (0.1, 0.2)))
    ) as pdf:
        page = pdf.pages[0]
        annot = page.hyperlinks[0]
        x0, y0, x1, y1 = annot["data"]["Rect"]
        assert pdfplumber.utils.obj_to_bbox(annot) == (
            x0,
            page.height - y1,
            x1,
            page.height - y0,
        )
