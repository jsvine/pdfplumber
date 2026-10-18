from pathlib import Path

import PIL.Image
import PIL.ImageDraw
import pytest

import pdfplumber
from pdfplumber import utils
from pdfplumber.display import PageImage
from pdfplumber.table import TableFinder, merge_edges

PDFS = Path(__file__).parent / "pdfs"


@pytest.fixture
def page():
    with pdfplumber.open(PDFS / "issue-140-example.pdf") as pdf:
        yield pdf.pages[0]


def blank_image(page, scale=1):
    return PageImage(
        page,
        original=PIL.Image.new(
            "RGB",
            (
                int((page.cropbox[2] - page.cropbox[0]) * scale),
                int((page.cropbox[3] - page.cropbox[1]) * scale),
            ),
            "white",
        ),
    )


@pytest.mark.parametrize("orientation", ["h", "v"])
@pytest.mark.parametrize("operation", ["join", "snap", "join_and_snap"])
@pytest.mark.parametrize("reverse_points", [False, True])
def test_draw_merged_edges(page, orientation, operation, reverse_points):
    # The original point lists remain attached to edges after joining/snapping.
    # Their bounding boxes are the geometry used by the table finder.
    point_sets = [[(20, 40), (50, 40)], [(50, 40), (80, 40)]]
    if operation != "join":
        point_sets[1] = [(x, y + 2) for x, y in point_sets[1]]
    if orientation == "v":
        point_sets = [[(y, x) for x, y in points] for points in point_sets]
    if reverse_points:
        point_sets = [points[::-1] for points in point_sets]

    lines = []
    for points in point_sets:
        x0, x1 = sorted(p[0] for p in points)
        top, bottom = sorted(p[1] for p in points)
        lines.append(
            utils.line_to_edge(
                {
                    "object_type": "line",
                    "pts": points,
                    "x0": x0,
                    "x1": x1,
                    "top": top,
                    "bottom": bottom,
                    "width": x1 - x0,
                    "height": bottom - top,
                }
            )
        )
    edges = merge_edges(
        lines,
        snap_x_tolerance=3 if operation != "join" else 0,
        snap_y_tolerance=3 if operation != "join" else 0,
        join_x_tolerance=-1 if operation == "snap" else 0,
        join_y_tolerance=-1 if operation == "snap" else 0,
    )
    assert len(edges) == (2 if operation == "snap" else 1)
    im = blank_image(page).draw_lines(edges, stroke="red")
    position = 40 if operation == "join" else 41
    expected = PIL.Image.new("RGB", im.original.size, "white")
    points = [(20, position), (80, position)]
    if orientation == "v":
        points = [(y, x) for x, y in points]
    PIL.ImageDraw.Draw(expected).line(points, fill="red")
    assert im.annotated.tobytes() == expected.tobytes()
    assert [line["pts"] for line in lines] == point_sets


@pytest.mark.parametrize("edge_index", range(4))
def test_draw_one_rectangle_edge(page, edge_index):
    rect = {
        "object_type": "rect",
        "x0": 20,
        "x1": 80,
        "top": 30,
        "bottom": 70,
        "y0": 100,
        "y1": 140,
        "doctop": 30,
        "width": 60,
        "height": 40,
        "pts": [(20, 30), (80, 30), (80, 70), (20, 70), (20, 30)],
    }
    edge = utils.rect_to_edges(rect)[edge_index]
    im = blank_image(page).draw_line(edge, stroke="red")
    expected = PIL.Image.new("RGB", im.original.size, "white")
    PIL.ImageDraw.Draw(expected).line(
        [(edge["x0"], edge["top"]), (edge["x1"], edge["bottom"])], fill="red"
    )
    assert im.annotated.tobytes() == expected.tobytes()


@pytest.mark.parametrize("kind", ["list", "tuple", "curve", "diagonal"])
def test_draw_original_point_paths(page, kind):
    points = [(20, 20), (50, 70), (80, 20)]
    if kind == "list":
        obj = points
    elif kind == "tuple":
        obj = tuple(points)
    else:
        obj = {"object_type": "curve", "pts": points}
        if kind == "diagonal":
            obj["orientation"] = None
    im = blank_image(page).draw_line(obj, stroke="red")
    expected = PIL.Image.new("RGB", im.original.size, "white")
    PIL.ImageDraw.Draw(expected).line(points, fill="red")
    assert im.annotated.tobytes() == expected.tobytes()


@pytest.mark.parametrize("scale", [1, 2])
@pytest.mark.parametrize("cropped", [False, True])
def test_debug_tablefinder_renders_merged_pdf_lines(page, scale, cropped):
    if cropped:
        page = page.crop((5, 10, page.width - 5, page.height - 10))
    page = page.filter(lambda obj: obj["object_type"] == "line" and obj["height"] == 0)
    finder = TableFinder(page)
    assert finder.edges
    assert not finder.tables
    assert not finder.intersections
    im = blank_image(page, scale)
    expected = im.original.copy()
    draw = PIL.ImageDraw.Draw(expected, "RGBA")
    for edge in finder.edges:
        draw.line(
            [
                im._reproject((edge["x0"], edge["top"])),
                im._reproject((edge["x1"], edge["bottom"])),
            ],
            fill=(255, 0, 0, 200),
        )
    im.debug_tablefinder(finder)
    assert im.annotated.tobytes() == expected.tobytes()
