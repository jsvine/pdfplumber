# PDFPlumber `v0.6.0-alpha`

Plumb a PDF for detailed information about each text character, rectangle, and line. Plus: Table extraction and visual debugging.

Works best on machine-generated, rather than scanned, PDFs. Built on [`pdfminer`](https://github.com/euske/pdfminer) and [`pdfminer.six`](https://github.com/goulu/pdfminer). 

Currently [tested](tests/) on [Python 2.7, 3.1, 3.4, 3.5, and 3.6](tox.ini).

## Table of Contents

- [Installation](#installation)
- [Command line interface](#command-line-interface)
- [Python library](#python-library)
- [Visual debugging](#visual-debugging)
- [Extracting tables](#extracting-tables)
- [Demonstrations](#demonstrations)
- [Acknowledgments / Contributors](#acknowledgments--contributors)
- [Contributing](#contributing)

## Installation

```sh
pip install pdfplumber
```

To use `pdfplumber`'s visual-debugging tools, you'll also need to have [`ImageMagick`](https://www.imagemagick.org/) installed on your computer. [Installation instructions here](http://docs.wand-py.org/en/latest/guide/install.html#install-imagemagick-debian).

## Command line interface

### Basic example

```sh
curl "https://cdn.rawgit.com/jsvine/pdfplumber/master/examples/pdfs/background-checks.pdf" > background-checks.pdf
pdfplumber < background-checks.pdf > background-checks.csv
```

The output will be a CSV containing info about every character, line, and rectangle in the PDF.

### Options

| Argument | Description |
|----------|-------------|
|`--format [format]`| `csv` or `json`. The `json` format returns slightly more information; it includes PDF-level metadata and height/width information about each page.|
|`--pages [list of pages]`| A space-delimited, `1`-indexed list of pages or hyphenated page ranges. E.g., `1, 11-15`, which would return data for pages 1, 11, 12, 13, 14, and 15.|
|`--types [list of object types to extract]`| Choices are `char`, `line`, `curve`, `rect`, `rect_edge`. Defaults to `char`, `line`, `curve`, `rect`.|

## Python library

### Basic example

```python
import pdfplumber

with pdfplumber.open("path/to/file.pdf") as pdf:
    first_page = pdf.pages[0]
    print(first_page.chars[0])
```

### Loading a PDF

`pdfplumber` provides two main ways to load a PDF:

- `pdfplumber.open("path/to/file.pdf")`
- `pdfplumber.load(file_like_object)`

Both methods return an instance of the `pdfplumber.PDF` class.

### The `pdfplumber.PDF` class

The top-level `pdfplumber.PDF` class represents a single PDF and has two main properties:

| Property | Description |
|----------|-------------|
|`.metadata`| A dictionary of metadata key/value pairs, drawn from the PDF's `Info` trailers. Typically includes "CreationDate," "ModDate," "Producer," et cetera.|
|`.pages`| A list containing one `pdfplumber.Page` instance per page loaded.|

### The `pdfplumber.Page` class

The `pdfplumber.Page` class is at the core of `pdfplumber`. Most things you'll do with `pdfplumber` will revolve around this class. It has these main properties:

| Property | Description |
|----------|-------------|
|`.page_number`| The sequential page number, starting with `1` for the first page, `2` for the second, and so on.|
|`.width`| The page's width.|
|`.height`| The page's height.|
|`.objects` / `.chars` / `.lines` / `.rects`| Each of these properties is a list, and each list contains one dictionary for each such object embedded on the page. For more detail, see "[Objects](#objects)" below.|

... and these main methods:

| Method | Description |
|--------|-------------|
|`.crop(bounding_box, char_threshold=0.5)`| Returns a version of the page cropped to the bounding box, which should be expressed as 4-tuple with the values `(x0, top, x1, bottom)`. Cropped pages retain objects that fall at least partly within the bounding box. If an object falls only partly within the box, its dimensions are sliced to fit the bounding box. If a character object's area is reduced by more than a ratio of `char_threshold`, it is removed.|
|`.within_bbox(bounding_box)`| Similar to `.crop`, but only retains objects that fall *entirely* within the bounding box.|
|`.filter(test_function)`| Returns a version of the page with only the `.objects` for which `test_function(obj)` returns `True`.|
|`.extract_text(x_tolerance = 3, y_tolerance = 3)`| Collates all of the page's character objects into a single string. Adds spaces where the difference between the `x1` of one character and the `x0` of the next is greater than `x_tolerance`. Adds newline characters where the difference between the `doctop` of one character and the `doctop` of the next is greater than `y_tolerance`.|
|`.extract_words(x_tolerance = 3, y_tolerance = 3, fontsize_tolerance = 0.25, keep_blank_chars = False, match_fontsize = True, match_fontname = True)`| Returns a list of all word-looking things and their bounding boxes. Words are considered to be sequences of characters where the difference between the `x1` of one character and the `x0` of the next is less than or equal to `x_tolerance` *and* where the `doctop` of one character and the `doctop` of the next is less than or equal to `y_tolerance`. By default, characters are grouped into the same word only if they share the same font and their font sizes are within `fontsize_tolerance` of each other. Those defaults can be changed by setting `match_fontname` and/or `match_fontsize` to `False`.|
|`.find_text_edges(orientation, min_words = 3, extend = False, word_kwargs = {})`| Returns a list edges that align with the borders of least `min_words`. The `orientation` parameter must be either `h` or `v` — i.e., horizontal or vertical. By default, the edges extend only to the outermost matching words; setting `extend = True` extends all edges to the extremity of the page. The `word_kwargs` dict is passed to `page.extract_words(...)`|
|`.extract_tables(table_settings)`| Extracts tabular data from the page. For more details see "[Extracting tables](#extracting-tables)" below.|
|`.extract_table(table_settings)`| Extracts data from the largest detected table on the page, as measured by the number of cells. For more details see "[Extracting tables](#extracting-tables)" below.|
|`.to_image(**conversion_kwargs)`| Returns an instance of the `PageImage` class. For more details, see "[Visual debugging](#visual-debugging)" below. For conversion_kwargs, see [here](http://docs.wand-py.org/en/latest/wand/image.html#wand.image.Image).|

### Objects

Each instance of `pdfplumber.PDF` and `pdfplumber.Page` provides access to four types of PDF objects. The following properties each return a Python list of the matching objects:

- `.chars`, each representing a single text character.
- `.lines`, each representing a single 1-dimensional line.
- `.rects`, each representing a single 2-dimensional rectangle.
- `.rect_edges`, each representing one side of each rectangle.
- `.edges`, equivalent to `.lines` + `.rect_edges`, with the addition of an "orientation" property for all objects.
- `.horizontal_edges` (same as above, but only for those running horizontally)
- `.vertical_edges` (same as above, but only for those running horizontally)
- `.curves`, each representing a series of connected points.

Each object is represented as a simple Python `dict`, with the following properties:

#### `char` properties

| Property | Description |
|----------|-------------|
|`page_number`| Page number on which this character was found.|
|`text`| E.g., "z", or "Z" or " ".|
|`fontname`| Name of the character's font face.|
|`size`| Font size.|
|`adv`| Equal to text width * the font size * scaling factor.|
|`upright`| Whether the character is upright.|
|`height`| Height of the character.|
|`width`| Width of the character.|
|`x0`| Distance of left side of character from left side of page.|
|`x1`| Distance of right side of character from left side of page.|
|`y0`| Distance of bottom of character from bottom of page.|
|`y1`| Distance of top of character from bottom of page.|
|`top`| Distance of top of character from top of page.|
|`bottom`| Distance of bottom of the character from top of page.|
|`doctop`| Distance of top of character from top of document.|
|`object_type`| "char" |

#### `line` properties

| Property | Description |
|----------|-------------|
|`page_number`| Page number on which this line was found.|
|`height`| Height of line.|
|`width`| Width of line.|
|`x0`| Distance of left-side extremity from left side of page.|
|`x1`| Distance of right-side extremity from left side of page.|
|`y0`| Distance of bottom extremity from bottom of page.|
|`y1`| Distance of top extremity bottom of page.|
|`top`| Distance of top of line from top of page.|
|`bottom`| Distance of bottom of the line from top of page.|
|`doctop`| Distance of top of line from top of document.|
|`linewidth`| Thickness of line.|
|`object_type`| "line"|

#### `rect` properties

| Property | Description |
|----------|-------------|
|`page_number`| Page number on which this rectangle was found.|
|`height`| Height of rectangle.|
|`width`| Width of rectangle.|
|`x0`| Distance of left side of rectangle from left side of page.|
|`x1`| Distance of right side of rectangle from left side of page.|
|`y0`| Distance of bottom of rectangle from bottom of page.|
|`y1`| Distance of top of rectangle from bottom of page.|
|`top`| Distance of top of rectangle from top of page.|
|`bottom`| Distance of bottom of the rectangle from top of page.|
|`doctop`| Distance of top of rectangle from top of document.|
|`linewidth`| Thickness of line.|
|`object_type`| "rect"|

#### `curve` properties

| Property | Description |
|----------|-------------|
|`page_number`| Page number on which this curve was found.|
|`points`| Points — as a list of `(x, top)` tuples — describing the curve.|
|`height`| Height of curve's bounding box.|
|`width`| Width of curve's bounding box.|
|`x0`| Distance of curve's left-most point from left side of page.|
|`x1`| Distance of curve's right-most point from left side of the page.|
|`y0`| Distance of curve's lowest point from bottom of page.|
|`y1`| Distance of curve's highest point from bottom of page.|
|`top`| Distance of curve's highest point from top of page.|
|`bottom`| Distance of curve's lowest point from top of page.|
|`doctop`| Distance of curve's highest point from top of document.|
|`linewidth`| Thickness of line.|
|`object_type`| "curve"|

Additionally, both `pdfplumber.PDF` and `pdfplumber.Page` provide access to two derived lists of objects: `.rect_edges` (which decomposes each rectangle into its four lines) and `.edges` (which combines `.rect_edges` with `.lines`). 

## Visual debugging

### Creating a `PageImage` with `.to_image()`

To turn any page (including cropped pages) into an `PageImage` object, call `my_page.to_image()`. You can optionally pass a `resolution={integer}` keyword argument, which defaults to 72. E.g.:

```python
im = my_pdf.page[0].to_image(resolution=150)
```

`PageImage` objects play nicely with IPython/Jupyter notebooks; they automatically render as cell outputs. For example:

![Visual debugging in Jupyter](examples/screenshots/visual-debugging-in-jupyter.png "Visual debugging in Jupyter")


### Basic `PageImage` methods

| Method | Description |
|--------|-------------|
|`im.reset()`| Clears anything you've drawn so far.|
|`im.copy()`| Copies the image to a new `PageImage` object.|
|`im.save(path_or_fileobject, format="PNG")`| Saves the annotated image.|

### Drawing methods

You can pass explicit coordinates or any `pdfplumber` PDF object (e.g., char, line, rect) to these methods.

| Single-object method | Bulk method | Description |
|----------------------|-------------|-------------|
|`im.draw_line(line, stroke={color}, stroke_width=1)`| `im.draw_lines(list_of_lines, **kwargs)`| Draws a line from a `line`, `curve`, or a 2-tuple of 2-tuples (e.g., `((x, y), (x, y))`).|
|`im.draw_vline(location, stroke={color}, stroke_width=1)`| `im.draw_vlines(list_of_locations, **kwargs)`| Draws a vertical line at the x-coordinate indicated by `location`.|
|`im.draw_hline(location, stroke={color}, stroke_width=1)`| `im.draw_hlines(list_of_locations, **kwargs)`| Draws a horizontal line at the y-coordinate indicated by `location`.|
|`im.draw_rect(bbox_or_obj, fill={color}, stroke={color}, stroke_width=1)`| `im.draw_rects(list_of_rects, **kwargs)`| Draws a rectangle from a `rect`, `char`, etc., or 4-tuple bounding box.|
|`im.draw_circle(center_or_obj, radius=5, fill={color}, stroke={color})`| `im.draw_circles(list_of_circles, **kwargs)`| Draws a circle at `(x, y)` coordinate or at the center of a `char`, `rect`, etc.|

Note: The methods above are built on Pillow's [`ImageDraw` methods](http://pillow.readthedocs.io/en/latest/reference/ImageDraw.html), but the parameters have been tweaked for consistency with SVG's `fill`/`stroke`/`stroke_width` nomenclature.

## Extracting tables

`pdfplumber`'s approach to table detection borrows heavily from [Anssi Nurminen's master's thesis](http://dspace.cc.tut.fi/dpub/bitstream/handle/123456789/21520/Nurminen.pdf?sequence=3), and is inspired by [Tabula](https://github.com/tabulapdf/tabula-extractor/issues/16). It works like this:

1. For any given PDF page, find the lines that are (a) explicitly defined and/or (b) implied by the alignment of words on the page.
2. Merge overlapping, or nearly-overlapping, lines.
3. Find the intersections of all those lines.
4. Find the most granular set of rectangles (i.e., cells) that use these intersections as their vertices.
5. Group contiguous cells into tables. 

### Table-extraction methods

`pdfplumber.Page` objects can call the following table methods:

| Method | Description |
|--------|-------------|
|`.find_tables(table_settings={})`|Returns a list of `Table` objects. The `Table` object provides access to the `.cells`, `.rows`, and `.bbox` properties, as well as the `.extract(x_tolerance=3, y_tolerance=3)` method.|
|`.extract_tables(table_settings={})`|Returns the text extracted from *all* tables found on the page, represented as a list of lists of lists, with the structure `table -> row -> cell`.|
|`.extract_table(table_settings={})`|Returns the text extracted from the *largest* table on the page, represented as a list of lists, with the structure `row -> cell`. (If multiple tables have the same size — as measured by the number of cells — this method returns the table closest to the top of the page.)|
|`.debug_tablefinder(table_settings={})`|Returns an instance of the `TableFinder` class, with access to the `.edges`, `.intersections`, `.cells`, and `.tables` properties.|

For example:

```python
pdf = pdfplumber.open("path/to/my.pdf")
page = pdf.pages[0]
page.extract_table()
```

[Click here for a more detailed example.](examples/notebooks/extract-table-ca-warn-report.ipynb)

### Table-extraction settings

By default, `extract_tables` uses the page's vertical and horizontal lines (or rectangle edges) as cell-separators. But the method is highly customizable via the `table_settings` argument. The possible settings, and their defaults:

```python
{
    "vertical_edges": None,
    "horizontal_edges": None,
    "snap_tolerance": DEFAULT_SNAP_TOLERANCE,
    "join_tolerance": DEFAULT_JOIN_TOLERANCE,
    "intersection_tolerance": 3,
    "intersection_x_tolerance": None,
    "intersection_y_tolerance": None,
    "text_kwargs": {}
}
```

| Setting | Description |
|---------|-------------|
|`"vertical_edges"`| A list of vertical edges/lines that explicitly demarcate cells in the table. Items in the list should be ewther numbers — indicating the `x` coordinate of a line the full height of the page — or a dictionary describing the line, with at least the following keys: `x`, `top`, `bottom`. |
|`"horizontal_edges"`| A list of horizontal edges/lines that explicitly demarcate cells in the table. Can be used in combination with any of the strategies above. Items in the list should be either numbers — indicating the `y` coordinate of a line the full height of the page — or a dictionary describing the line, with at least the following keys: `top`, `x0`, `x1`.|
|`"snap_tolerance"`| Parallel lines within `snap_tolerance` pixels will be "snapped" to the same horizontal or vertical position.|
|`"join_tolerance"`| Line segments on the same infinite line, and whose ends are within `join_tolerance` of one another, will be "joined" into a single line segment.|
|`"intersection_tolerance"`, `"intersection_x_tolerance"`, `"intersection_y_tolerance"`| When combining edges into cells, orthogonal edges must be within `intersection_tolerance` pixels to be considered intersecting.|
|`"text_kwargs"`| Arguments to be passed to `utils.extract_text` inside each table cell.|

### Notes

- Often it's helpful to crop a page — `Page.crop(bounding_box)` — before trying to extract the table.

- Using `Page.find_text_edges(...)` often works well for extracting tables where the text is well-aligned but missing explicit boundary lines.

- Table extraction for `pdfplumber` was radically redesigned for `v0.6.0`, and introduced breaking changes.


## Demonstrations

- [Using `extract_table` on a California Worker Adjustment and Retraining Notification (WARN) report](examples/notebooks/extract-table-ca-warn-report.ipynb). Demonstrates basic visual debugging and table extraction.
- [Using `extract_table` on the FBI's National Instant Criminal Background Check System PDFs](examples/notebooks/extract-table-nics.ipynb). Demonstrates how to use visual debugging to find optimal table extraction settings. Also demonstrates `Page.crop(...)` and `Page.extract_text(...).`
- [Inspecting and visualizing `curve` objects](examples/notebooks/ag-energy-roundup-curves.ipynb).
- [Extracting fixed-width data from a San Jose PD firearm search report](examples/notebooks/san-jose-pd-firearm-report.ipynb), an example of using `Page.extract_text(...)`.

## Acknowledgments / Contributors

Many thanks to the following users who've contributed ideas, features, and fixes:

- [Jacob Fenton](https://github.com/jsfenfen)
- [Dan Nguyen](https://github.com/dannguyen)
- [Jeff Barrera](https://github.com/jeffbarrera)
- [Bob Lannon](https://github.com/boblannon)

## Contributing

Pull requests are welcome, but please submit an issue (or email jsvine@gmail.com) before submitting one, as the library is in active development. The current development branch is `v0.6.0`.
