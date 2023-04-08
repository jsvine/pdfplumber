from io import BufferedReader, BytesIO
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

import PIL.Image
import PIL.ImageDraw
from wand.image import Color as WandColor  # type: ignore
from wand.image import Image as WandImage

from . import utils
from ._typing import T_bbox, T_num, T_obj, T_obj_list, T_point, T_seq
from .table import T_table_settings, Table, TableFinder, TableSettings

if TYPE_CHECKING:  # pragma: nocover
    from pandas.core.frame import DataFrame
    from pandas.core.series import Series

    from .page import Page


class COLORS:
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    TRANSPARENT = (0, 0, 0, 0)


DEFAULT_FILL = COLORS.BLUE + (50,)
DEFAULT_STROKE = COLORS.RED + (200,)
DEFAULT_STROKE_WIDTH = 1
DEFAULT_RESOLUTION = 72

T_color = Union[Tuple[int, int, int], Tuple[int, int, int, int], str]
T_contains_points = Union[Tuple[T_point, ...], List[T_point], T_obj]


def get_page_image(
    stream: Union[BufferedReader, BytesIO], page_no: int, resolution: Union[int, float]
) -> WandImage:
    # If we are working with a file object saved to disk
    if hasattr(stream, "name"):
        filename = f"{stream.name}[{page_no}]"
        file = None

        def postprocess(img: WandImage) -> WandImage:
            return img

    # If we instead are working with a BytesIO stream
    else:
        stream.seek(0)
        filename = None
        file = stream

        def postprocess(img: WandImage) -> WandImage:
            return WandImage(image=img.sequence[page_no])

    with WandImage(
        resolution=resolution,
        filename=filename,
        file=file,
        colorspace="rgb",
        format="pdf",
    ) as img_init:
        img = postprocess(img_init)
        with WandImage(
            width=img.width,
            height=img.height,
            background=WandColor("white"),
            colorspace="rgb",
        ) as bg:
            bg.composite(img, 0, 0)
            try:
                im = PIL.Image.open(BytesIO(bg.make_blob("png")))
            except PIL.Image.DecompressionBombError:
                raise PIL.Image.DecompressionBombError(
                    "Image conversion raised a DecompressionBombError. "
                    "PIL.Image.MAX_IMAGE_PIXELS is currently set to "
                    f"{PIL.Image.MAX_IMAGE_PIXELS}. "
                    "If you trust this PDF, you can try setting "
                    "PIL.Image.MAX_IMAGE_PIXELS to a higher value. "
                    "See https://github.com/jsvine/pdfplumber/issues/413"
                    "#issuecomment-1190650404 for more information."
                )
        return im.convert("RGB")


class PageImage:
    def __init__(
        self,
        page: "Page",
        original: Optional[WandImage] = None,
        resolution: Union[int, float] = DEFAULT_RESOLUTION,
    ):
        self.page = page
        if original is None:
            self.original = get_page_image(
                page.pdf.stream, page.page_number - 1, resolution
            )
        else:
            self.original = original

        if page.is_original:
            self.root = page
            cropped = False
        else:
            self.root = page.root_page
            cropped = page.root_page.bbox != page.bbox
        self.scale = self.original.size[0] / self.root.width
        if cropped:
            cropbox = (
                (page.bbox[0] - page.root_page.bbox[0]) * self.scale,
                (page.bbox[1] - page.root_page.bbox[1]) * self.scale,
                (page.bbox[2] - page.root_page.bbox[0]) * self.scale,
                (page.bbox[3] - page.root_page.bbox[1]) * self.scale,
            )
            self.original = self.original.crop(tuple(map(int, cropbox)))
        self.reset()

    def _reproject_bbox(self, bbox: T_bbox) -> T_bbox:
        x0, top, x1, bottom = bbox
        _x0, _top = self._reproject((x0, top))
        _x1, _bottom = self._reproject((x1, bottom))
        return (_x0, _top, _x1, _bottom)

    def _reproject(self, coord: T_point) -> T_point:
        """
        Given an (x0, top) tuple from the *root* coordinate system,
        return an (x0, top) tuple in the *image* coordinate system.
        """
        x0, top = coord
        px0, ptop = self.page.bbox[:2]
        rx0, rtop = self.root.bbox[:2]
        _x0 = (x0 + rx0 - px0) * self.scale
        _top = (top + rtop - ptop) * self.scale
        return (_x0, _top)

    def reset(self) -> "PageImage":
        self.annotated = PIL.Image.new(self.original.mode, self.original.size)
        self.annotated.paste(self.original)
        self.draw = PIL.ImageDraw.Draw(self.annotated, "RGBA")
        self.save = self.annotated.save
        return self

    def copy(self) -> "PageImage":
        return self.__class__(self.page, self.original)

    def draw_line(
        self,
        points_or_obj: T_contains_points,
        stroke: T_color = DEFAULT_STROKE,
        stroke_width: int = DEFAULT_STROKE_WIDTH,
    ) -> "PageImage":
        # If passing a raw list of points, use those
        if isinstance(points_or_obj, (tuple, list)):
            points = points_or_obj
        # Else, use the "pts" attribute if available
        elif isinstance(points_or_obj, dict) and "pts" in points_or_obj:
            points = [(x, y) for x, y in points_or_obj["pts"]]
        # Otherwise, just use ((x0, top), (x1, bottom))
        else:
            obj = points_or_obj
            points = ((obj["x0"], obj["top"]), (obj["x1"], obj["bottom"]))

        self.draw.line(
            list(map(self._reproject, points)), fill=stroke, width=stroke_width
        )

        return self

    def draw_lines(
        self,
        list_of_lines: Union[T_seq[T_contains_points], "DataFrame"],
        stroke: T_color = DEFAULT_STROKE,
        stroke_width: int = DEFAULT_STROKE_WIDTH,
    ) -> "PageImage":
        for x in utils.to_list(list_of_lines):
            self.draw_line(x, stroke=stroke, stroke_width=stroke_width)
        return self

    def draw_vline(
        self,
        location: T_num,
        stroke: T_color = DEFAULT_STROKE,
        stroke_width: int = DEFAULT_STROKE_WIDTH,
    ) -> "PageImage":
        points = (location, self.page.bbox[1], location, self.page.bbox[3])
        self.draw.line(self._reproject_bbox(points), fill=stroke, width=stroke_width)
        return self

    def draw_vlines(
        self,
        locations: Union[List[T_num], "Series"],
        stroke: T_color = DEFAULT_STROKE,
        stroke_width: int = DEFAULT_STROKE_WIDTH,
    ) -> "PageImage":
        for x in list(locations):
            self.draw_vline(x, stroke=stroke, stroke_width=stroke_width)
        return self

    def draw_hline(
        self,
        location: T_num,
        stroke: T_color = DEFAULT_STROKE,
        stroke_width: int = DEFAULT_STROKE_WIDTH,
    ) -> "PageImage":
        points = (self.page.bbox[0], location, self.page.bbox[2], location)
        self.draw.line(self._reproject_bbox(points), fill=stroke, width=stroke_width)
        return self

    def draw_hlines(
        self,
        locations: Union[List[T_num], "Series"],
        stroke: T_color = DEFAULT_STROKE,
        stroke_width: int = DEFAULT_STROKE_WIDTH,
    ) -> "PageImage":
        for x in list(locations):
            self.draw_hline(x, stroke=stroke, stroke_width=stroke_width)
        return self

    def draw_rect(
        self,
        bbox_or_obj: Union[T_bbox, T_obj],
        fill: T_color = DEFAULT_FILL,
        stroke: T_color = DEFAULT_STROKE,
        stroke_width: int = DEFAULT_STROKE_WIDTH,
    ) -> "PageImage":
        if isinstance(bbox_or_obj, (tuple, list)):
            bbox = bbox_or_obj
        else:
            obj = bbox_or_obj
            bbox = (obj["x0"], obj["top"], obj["x1"], obj["bottom"])

        x0, top, x1, bottom = bbox
        half = stroke_width / 2
        x0 = min(x0 + half, (x0 + x1) / 2)
        top = min(top + half, (top + bottom) / 2)
        x1 = max(x1 - half, (x0 + x1) / 2)
        bottom = max(bottom - half, (top + bottom) / 2)

        fill_bbox = self._reproject_bbox((x0, top, x1, bottom))
        self.draw.rectangle(fill_bbox, fill, COLORS.TRANSPARENT)

        if stroke_width > 0:
            segments = [
                ((x0, top), (x1, top)),  # top
                ((x0, bottom), (x1, bottom)),  # bottom
                ((x0, top), (x0, bottom)),  # left
                ((x1, top), (x1, bottom)),  # right
            ]
            self.draw_lines(segments, stroke=stroke, stroke_width=stroke_width)
        return self

    def draw_rects(
        self,
        list_of_rects: Union[List[T_bbox], T_obj_list, "DataFrame"],
        fill: T_color = DEFAULT_FILL,
        stroke: T_color = DEFAULT_STROKE,
        stroke_width: int = DEFAULT_STROKE_WIDTH,
    ) -> "PageImage":
        for x in utils.to_list(list_of_rects):
            self.draw_rect(x, fill=fill, stroke=stroke, stroke_width=stroke_width)
        return self

    def draw_circle(
        self,
        center_or_obj: Union[T_point, T_obj],
        radius: int = 5,
        fill: T_color = DEFAULT_FILL,
        stroke: T_color = DEFAULT_STROKE,
    ) -> "PageImage":
        if isinstance(center_or_obj, tuple):
            center = center_or_obj
        else:
            obj = center_or_obj
            center = ((obj["x0"] + obj["x1"]) / 2, (obj["top"] + obj["bottom"]) / 2)
        cx, cy = center
        bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
        self.draw.ellipse(self._reproject_bbox(bbox), fill, stroke)
        return self

    def draw_circles(
        self,
        list_of_circles: Union[List[T_point], T_obj_list, "DataFrame"],
        radius: int = 5,
        fill: T_color = DEFAULT_FILL,
        stroke: T_color = DEFAULT_STROKE,
    ) -> "PageImage":
        for x in utils.to_list(list_of_circles):
            self.draw_circle(x, radius=radius, fill=fill, stroke=stroke)
        return self

    def debug_table(
        self,
        table: Table,
        fill: T_color = DEFAULT_FILL,
        stroke: T_color = DEFAULT_STROKE,
        stroke_width: int = 1,
    ) -> "PageImage":
        """
        Outline all found tables.
        """
        self.draw_rects(
            table.cells, fill=fill, stroke=stroke, stroke_width=stroke_width
        )
        return self

    def debug_tablefinder(
        self, tf: Optional[Union[TableFinder, TableSettings, T_table_settings]] = None
    ) -> "PageImage":
        if isinstance(tf, TableFinder):
            finder = tf
        elif tf is None or isinstance(tf, (TableSettings, dict)):
            finder = self.page.debug_tablefinder(tf)
        else:
            raise ValueError(
                "Argument must be instance of TableFinder"
                "or a TableFinder settings dict."
            )

        for table in finder.tables:
            self.debug_table(table)

        self.draw_lines(finder.edges, stroke_width=1)

        self.draw_circles(
            list(finder.intersections.keys()),
            fill=COLORS.TRANSPARENT,
            stroke=COLORS.BLUE + (200,),
            radius=3,
        )
        return self

    def outline_words(
        self,
        stroke: T_color = DEFAULT_STROKE,
        fill: T_color = DEFAULT_FILL,
        stroke_width: int = DEFAULT_STROKE_WIDTH,
        x_tolerance: T_num = utils.DEFAULT_X_TOLERANCE,
        y_tolerance: T_num = utils.DEFAULT_Y_TOLERANCE,
    ) -> "PageImage":

        words = self.page.extract_words(
            x_tolerance=x_tolerance, y_tolerance=y_tolerance
        )
        self.draw_rects(words, stroke=stroke, fill=fill, stroke_width=stroke_width)
        return self

    def outline_chars(
        self,
        stroke: T_color = (255, 0, 0, 255),
        fill: T_color = (255, 0, 0, int(255 / 4)),
        stroke_width: int = DEFAULT_STROKE_WIDTH,
    ) -> "PageImage":

        self.draw_rects(
            self.page.chars, stroke=stroke, fill=fill, stroke_width=stroke_width
        )
        return self

    def _repr_png_(self) -> bytes:
        b = BytesIO()
        self.annotated.save(b, "PNG")
        return b.getvalue()

    def show(self) -> None:  # pragma: no cover
        self.annotated.show()
