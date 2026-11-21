import io

import pytest
from PIL import ImageChops

import pdfplumber


def make_pdf(rotation, origin=(0, 0), box_name="CropBox", full_page=False, reverse=0):
    ox, oy = origin
    box = (0, 0, 600, 400) if full_page else (60, 50, 310, 270)
    x0, y0, x1, y1 = box
    coords = [x0 + ox, y0 + oy, x1 + ox, y1 + oy]
    if reverse & 1:
        coords[0], coords[2] = coords[2], coords[0]
    if reverse & 2:
        coords[1], coords[3] = coords[3], coords[1]
    explicit = f"/{box_name} [{' '.join(map(str, coords))}]" if box_name else ""
    stream = f"0 1 0 rg {x0 + ox} {y0 + oy} {x1 - x0} {y1 - y0} re f".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [{ox} {oy} {ox + 600} {oy + 400}] "
            f"{explicit} /Rotate {rotation} /Resources << >> /Contents 4 0 R >>"
        ).encode(),
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(out)
    out.extend(b"xref\n0 5\n0000000000 65535 f \n")
    for offset in offsets:
        out.extend(f"{offset:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return io.BytesIO(out)


def green_bbox(image):
    red, green, blue = image.convert("RGB").split()
    return ImageChops.subtract(green, ImageChops.lighter(red, blue)).getbbox()


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("origin", [(0, 0), (20, 30), (-40, -70)])
@pytest.mark.parametrize("box_name", ["CropBox", "TrimBox", "BleedBox", "ArtBox"])
def test_explicit_page_box_matches_content(rotation, origin, box_name):
    with pdfplumber.open(make_pdf(rotation, origin, box_name)) as pdf:
        page = pdf.pages[0]
        # pdfminer transforms the content independently of page-box handling.
        expected = pdfplumber.utils.obj_to_bbox(page.rects[0])
        assert getattr(page, box_name.lower()) == expected


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("reverse", [0, 1, 2, 3])
def test_page_box_endpoint_order(rotation, reverse):
    with pdfplumber.open(make_pdf(rotation, reverse=reverse)) as pdf:
        page = pdf.pages[0]
        assert page.cropbox == pdfplumber.utils.obj_to_bbox(page.rects[0])


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("origin", [(0, 0), (20, 30), (-40, -70), (0.1, 0.2)])
@pytest.mark.parametrize("box_name", [None, "CropBox", "TrimBox", "BleedBox", "ArtBox"])
def test_page_box_defaults_and_full_page(rotation, origin, box_name):
    with pdfplumber.open(make_pdf(rotation, origin, box_name, full_page=True)) as pdf:
        page = pdf.pages[0]
        ox, oy = origin
        # Preserve the existing global-origin convention, including its offsets.
        expected_media = (
            (oy, -ox, oy + 400, 600 - ox)
            if rotation in (90, 270)
            else (ox, -oy, ox + 600, 400 - oy)
        )
        assert page.mediabox == pytest.approx(expected_media)
        assert page.bbox == page.mediabox
        assert page.cropbox == page.mediabox
        if box_name:
            assert getattr(page, box_name.lower()) == page.mediabox


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("origin", [(0, 0), (20, 30), (-40, -70)])
def test_rotated_crop_rendering(rotation, origin):
    with pdfplumber.open(make_pdf(rotation, origin)) as pdf:
        page = pdf.pages[0]
        bbox = pdfplumber.utils.obj_to_bbox(page.rects[0])
        # PDFium renders the original PDF; PageImage must place the cropped
        # bitmap in the same coordinate space as independently parsed content.
        cropped = page.crop(bbox).to_image(resolution=72).original
        assert cropped.size == (round(bbox[2] - bbox[0]), round(bbox[3] - bbox[1]))
        assert green_bbox(cropped) == (0, 0, cropped.width, cropped.height)
        media = page.to_image(resolution=72, force_mediabox=True).original
        left, top = page.mediabox[:2]
        assert green_bbox(media) == tuple(
            round(value - (left if i % 2 == 0 else top)) for i, value in enumerate(bbox)
        )
