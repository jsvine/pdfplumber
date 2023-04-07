# pdfplumber

[![Version](https://img.shields.io/pypi/v/pdfplumber.svg)](https://pypi.python.org/pypi/pdfplumber) ![Tests](https://github.com/jsvine/pdfplumber/workflows/Tests/badge.svg) [![Code coverage](https://codecov.io/gh/jsvine/pdfplumber/branch/stable/graph/badge.svg)](https://codecov.io/gh/jsvine/pdfplumber/branch/stable) [![Support Python versions](https://img.shields.io/pypi/pyversions/pdfplumber.svg)](https://pypi.python.org/pypi/pdfplumber)

Plumb a PDF for detailed information about each text character, rectangle, and line. Plus: Table extraction and visual debugging.

Works best on machine-generated, rather than scanned, PDFs. Built on [`pdfminer.six`](https://github.com/goulu/pdfminer). 

Currently [tested](tests/) on [Python 3.7, 3.8, 3.9, 3.10](.github/workflows/tests.yml).

Translations of this document are available in: [Chinese (by @hbh112233abc)](https://github.com/hbh112233abc/pdfplumber/blob/stable/README-CN.md).

__To report a bug__ or request a feature, please [file an issue](https://github.com/jsvine/pdfplumber/issues/new/choose). __To ask a question__ or request assistance with a specific PDF, please [use the discussions forum](https://github.com/jsvine/pdfplumber/discussions).

> 👋 This repository’s maintainers are available to hire for PDF data-extraction consulting projects. To get a cost estimate, contact [Jeremy](https://www.jsvine.com/consulting/pdf-data-extraction/) (for projects of any size or complexity) and/or [Samkit](https://www.linkedin.com/in/samkit-jain/) (specifically for table extraction).

## Table of Contents

- [Installation](#installation)
- [Command line interface](#command-line-interface)
- [Python library](#python-library)
- [Visual debugging](#visual-debugging)
- [Extracting text](#extracting-text)
- [Extracting tables](#extracting-tables)
- [Extracting form values](#extracting-form-values)
- [Demonstrations](#demonstrations)
- [Comparison to other libraries](#comparison-to-other-libraries)
- [Acknowledgments / Contributors](#acknowledgments--contributors)
- [Contributing](#contributing)

## Installation

```sh
pip install pdfplumber
```

## Command line interface

### Basic example

```sh
curl "https://raw.githubusercontent.com/jsvine/pdfplumber/stable/examples/pdfs/background-checks.pdf" > background-checks.pdf
pdfplumber < background-checks.pdf > background-checks.csv
```

The output will be a CSV containing info about every character, line, and rectangle in the PDF.

### Options

| Argument | Description |
|----------|-------------|
|`--format [format]`| `csv` or `json`. The `json` format returns more information; it includes PDF-level and page-level metadata, plus dictionary-nested attributes.|
|`--pages [list of pages]`| A space-delimited, `1`-indexed list of pages or hyphenated page ranges. E.g., `1, 11-15`, which would return data for pages 1, 11, 12, 13, 14, and 15.|
|`--types [list of object types to extract]`| Choices are `char`, `rect`, `line`, `curve`, `image`, `annot`, et cetera. Defaults to all available.|
|`--laparams`| A JSON-formatted string (e.g., `'{"detect_vertical": true}'`) to pass to `pdfplumber.open(..., laparams=...)`.|
|`--precision [integer]`| The number of decimal places to round floating-point numbers. Defaults to no rounding.|

## Python library

### Basic example

```python
import pdfplumber

with pdfplumber.open("path/to/file.pdf") as pdf:
    first_page = pdf.pages[0]
    print(first_page.chars[0])
```

### Loading a PDF

To start working with a PDF, call `pdfplumber.open(x)`, where `x` can be a:

- path to your PDF file
- file object, loaded as bytes
- file-like object, loaded as bytes

The `open` method returns an instance of the `pdfplumber.PDF` class.

To load a password-protected PDF, pass the `password` keyword argument, e.g., `pdfplumber.open("file.pdf", password = "test")`.

To set layout analysis parameters to `pdfminer.six`'s layout engine, pass the `laparams` keyword argument, e.g., `pdfplumber.open("file.pdf", laparams = { "line_overlap": 0.7 })`.

Invalid metadata values are treated as a warning by default. If that is not intended, pass `strict_metadata=True` to the `open` method and `pdfplumber.open` will raise an exception if it is unable to parse the metadata.

### The `pdfplumber.PDF` class

The top-level `pdfplumber.PDF` class represents a single PDF and has two main properties:

| Property | Description |
|----------|-------------|
|`.metadata`| A dictionary of metadata key/value pairs, drawn from the PDF's `Info` trailers. Typically includes "CreationDate," "ModDate," "Producer," et cetera.|
|`.pages`| A list containing one `pdfplumber.Page` instance per page loaded.|

... and also has the following method:

| Method | Description |
|--------|-------------|
|`.close()`| By default, `Page` objects cache their layout and object information to avoid having to reprocess it. When parsing large PDFs, however, these cached properties can require a lot of memory. You can use this method to flush the cache and release the memory. (In version `<= 0.5.25`, use `.flush_cache()`.)|

### The `pdfplumber.Page` class

The `pdfplumber.Page` class is at the core of `pdfplumber`. Most things you'll do with `pdfplumber` will revolve around this class. It has these main properties:

| Property | Description |
|----------|-------------|
|`.page_number`| The sequential page number, starting with `1` for the first page, `2` for the second, and so on.|
|`.width`| The page's width.|
|`.height`| The page's height.|
|`.objects` / `.chars` / `.lines` / `.rects` / `.curves` / `.images`| Each of these properties is a list, and each list contains one dictionary for each such object embedded on the page. For more detail, see "[Objects](#objects)" below.|

... and these main methods:

| Method | Description |
|--------|-------------|
|`.crop(bounding_box, relative=False, strict=True)`| Returns a version of the page cropped to the bounding box, which should be expressed as 4-tuple with the values `(x0, top, x1, bottom)`. Cropped pages retain objects that fall at least partly within the bounding box. If an object falls only partly within the box, its dimensions are sliced to fit the bounding box. If `relative=True`, the bounding box is calculated as an offset from the top-left of the page's bounding box, rather than an absolute positioning. (See [Issue #245](https://github.com/jsvine/pdfplumber/issues/245) for a visual example and explanation.) When `strict=True` (the default), the crop's bounding box must fall entirely within the page's bounding box.|
|`.within_bbox(bounding_box, relative=False, strict=True)`| Similar to `.crop`, but only retains objects that fall *entirely within* the bounding box.|
|`.outside_bbox(bounding_box, relative=False, strict=True)`| Similar to `.crop` and `.within_bbox`, but only retains objects that fall *entirely outside* the bounding box.|
|`.filter(test_function)`| Returns a version of the page with only the `.objects` for which `test_function(obj)` returns `True`.|

Additional methods are described in the sections below:

- [Visual debugging](#visual-debugging)
- [Extracting text](#extracting-text)
- [Extracting tables](#extracting-tables)

### Objects

Each instance of `pdfplumber.PDF` and `pdfplumber.Page` provides access to several types of PDF objects, all derived from [`pdfminer.six`](https://github.com/pdfminer/pdfminer.six/) PDF parsing. The following properties each return a Python list of the matching objects:

- `.chars`, each representing a single text character.
- `.lines`, each representing a single 1-dimensional line.
- `.rects`, each representing a single 2-dimensional rectangle.
- `.curves`, each representing any series of connected points that `pdfminer.six` does not recognize as a line or rectangle.
- `.images`, each representing an image.
- `.annots`, each representing a single PDF annotation (cf. Section 8.4 of the [official PDF specification](https://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/pdf_reference_1-7.pdf) for details)
- `.hyperlinks`, each representing a single PDF annotation of the subtype `Link` and having an `URI` action attribute

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
|`matrix`| The "current transformation matrix" for this character. (See below for details.)|
|`stroking_color`|The color of the character's outline (i.e., stroke), expressed as a tuple or integer, depending on the “color space” used.|
|`non_stroking_color`|The character's interior color.|
|`object_type`| "char"|

__Note__: A character’s `matrix` property represents the “current transformation matrix,” as described in Section 4.2.2 of the [PDF Reference](https://ghostscript.com/~robin/pdf_reference17.pdf) (6th Ed.). The matrix controls the character’s scale, skew, and positional translation. Rotation is a combination of scale and skew, but in most cases can be considered equal to the x-axis skew. The `pdfplumber.ctm` submodule defines a class, `CTM`, that assists with these calculations. For instance:

```python
from pdfplumber.ctm import CTM
my_char = pdf.pages[0].chars[3]
my_char_ctm = CTM(*my_char["matrix"])
my_char_rotation = my_char_ctm.skew_x
```

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
|`stroking_color`|The color of the line, expressed as a tuple or integer, depending on the “color space” used.|
|`non_stroking_color`|The non-stroking color specified for the line’s path.|
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
|`stroking_color`|The color of the rectangle's outline, expressed as a tuple or integer, depending on the “color space” used.|
|`non_stroking_color`|The rectangle’s fill color.|
|`object_type`| "rect"|

#### `curve` properties

| Property | Description |
|----------|-------------|
|`page_number`| Page number on which this curve was found.|
|`pts`| Points — as a list of `(x, top)` tuples — describing the curve.|
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
|`fill`| Whether the shape defined by the curve's path is filled.|
|`stroking_color`|The color of the curve's outline, expressed as a tuple or integer, depending on the “color space” used.|
|`non_stroking_color`|The curve’s fill color.|
|`object_type`| "curve"|

Additionally, both `pdfplumber.PDF` and `pdfplumber.Page` provide access to two derived lists of objects: `.rect_edges` (which decomposes each rectangle into its four lines) and `.edges` (which combines `.rect_edges` with `.lines`). 

#### `image` properties

[To be completed.]

### Obtaining higher-level layout objects via `pdfminer.six`

If you pass the `pdfminer.six`-handling `laparams` parameter to `pdfplumber.open(...)`, then each page's `.objects` dictionary will also contain `pdfminer.six`'s higher-level layout objects, such as `"textboxhorizontal"`.


## Visual debugging

`pdfplumber`'s visual debugging tools can be helpful in understanding the structure of a PDF and the objects that have been extracted from it.

__Note:__ To use this feature, you'll also need to have two additional pieces of software installed on your computer:

- [`ImageMagick`](https://www.imagemagick.org/). [Installation instructions here](http://docs.wand-py.org/en/latest/guide/install.html#install-imagemagick-debian).
- [`ghostscript`](https://www.ghostscript.com). [Installation instructions here](https://ghostscript.readthedocs.io/en/latest/Install.html), or simply `apt install ghostscript` (Ubuntu) / `brew install ghostscript` (Mac).


### Creating a `PageImage` with `.to_image()`

To turn any page (including cropped pages) into an `PageImage` object, call `my_page.to_image()`. You can optionally pass *one* of the  following keyword arguments:

- `resolution`: The desired number pixels per inch. Defaults to 72. See note below.
- `width`: The desired image width in pixels.
- `height`: The desired image width in pixels.

For instance:

```python
im = my_pdf.pages[0].to_image(resolution=150)
```

From a script or REPL, `im.show()` will open the image in your local image viewer. But `PageImage` objects also play nicely with IPython/Jupyter notebooks; they automatically render as cell outputs. For example:

![Visual debugging in Jupyter](examples/screenshots/visual-debugging-in-jupyter.png "Visual debugging in Jupyter")

*Note*: `pdfplumber` passes the `resolution` parameter to [Wand](https://docs.wand-py.org/en/latest/wand/image.html#wand.image.Image), the Python library we use for image conversion. Wand will create the image with the desired number of total pixels of height/width, but does not fully respect the `resolution` in the strict sense of that word: Although PNGs are capable of storing an image's resolution density as metadata, Wand's PNGs do not.

*Note*: `.to_image(...)` works as expected with `Page.crop(...)`/`CroppedPage` instances, but is unable to incorporate changes made via `Page.filter(...)`/`FilteredPage` instances.


### Basic `PageImage` methods

| Method | Description |
|--------|-------------|
|`im.reset()`| Clears anything you've drawn so far.|
|`im.copy()`| Copies the image to a new `PageImage` object.|
|`im.show()`| Opens the image in your local image viewer.|
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

### Troubleshooting ImageMagick on Debian-based systems

If you're using `pdfplumber` on a Debian-based system and encounter a `PolicyError`, you may be able to fix it by changing the following line in `/etc/ImageMagick-6/policy.xml` from this:

```xml
<policy domain="coder" rights="none" pattern="PDF" />
```

... to this:

```xml
<policy domain="coder" rights="read|write" pattern="PDF" />
```

(More details about `policy.xml` [available here](https://imagemagick.org/script/security-policy.php).)

## Extracting text

`pdfplumber` can extract text from any given page (including cropped and derived pages). It can also attempt to preserve the layout of that text, as well as to identify the coordinates of words and search queries. `Page` objects can call the following text-extraction methods:


| Method | Description |
|--------|-------------|
|`.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False, use_text_flow=False, horizontal_ltr=True, vertical_ttb=True, extra_attrs=[], split_at_punctuation=False)`| Returns a list of all word-looking things and their bounding boxes. Words are considered to be sequences of characters where (for "upright" characters) the difference between the `x1` of one character and the `x0` of the next is less than or equal to `x_tolerance` *and* where the `doctop` of one character and the `doctop` of the next is less than or equal to `y_tolerance`. A similar approach is taken for non-upright characters, but instead measuring the vertical, rather than horizontal, distances between them. The parameters `horizontal_ltr` and `vertical_ttb` indicate whether the words should be read from left-to-right (for horizontal words) / top-to-bottom (for vertical words). Changing `keep_blank_chars` to `True` will mean that blank characters are treated as part of a word, not as a space between words. Changing `use_text_flow` to `True` will use the PDF's underlying flow of characters as a guide for ordering and segmenting the words, rather than presorting the characters by x/y position. (This mimics how dragging a cursor highlights text in a PDF; as with that, the order does not always appear to be logical.) Passing a list of `extra_attrs`  (e.g., `["fontname", "size"]` will restrict each words to characters that share exactly the same value for each of those [attributes](#char-properties), and the resulting word dicts will indicate those attributes. Setting `split_at_punctuation` to `True` will enforce breaking tokens at punctuations specified by `string.punctuation`; or you can specify the list of separating punctuation by pass a string, e.g., <code>split_at_punctuation='!"&\'()*+,.:;<=>?@[\]^\`\{\|\}~'</code>.  |
|`.extract_text(x_tolerance=3, y_tolerance=3, layout=False, x_density=7.25, y_density=13, **kwargs)`| Collates all of the page's character objects into a single string.<ul><li><p>When `layout=False`: Adds spaces where the difference between the `x1` of one character and the `x0` of the next is greater than `x_tolerance`. Adds newline characters where the difference between the `doctop` of one character and the `doctop` of the next is greater than `y_tolerance`.</p></li><li><p>When `layout=True` (*experimental feature*): Attempts to mimic the structural layout of the text on the page(s), using `x_density` and `y_density` to determine the minimum number of characters/newlines per "point," the PDF unit of measurement. All remaining `**kwargs` are passed to `.extract_words(...)` (see above), the first step in calculating the layout.</p></li></ul>|
|`.extract_text_simple(x_tolerance=3, y_tolerance=3)`| A slightly faster but less flexible version of `.extract_text(...)`, using a simpler logic.|
|`.search(pattern, regex=True, case=True, **kwargs)`|*Experimental feature* that allows you to search a page's text, returning a list of all instances that match the query. For each instance, the response dictionary object contains the matching text, any regex group matches, the bounding box coordinates, and the char objects themselves. `pattern` can be a compiled regular expression, an uncompiled regular expression, or a non-regex string. If `regex` is `False`, the pattern is treated as a non-regex string. If `case` is `False`, the search is performed in a case-insensitive manner. The remaining `**kwargs` are those you would pass to `.extract_text(layout=True, ...)`.|
|`.dedupe_chars(tolerance=1)`| Returns a version of the page with duplicate chars — those sharing the same text, fontname, size, and positioning (within `tolerance` x/y) as other characters — removed. (See [Issue #71](https://github.com/jsvine/pdfplumber/issues/71) to understand the motivation.)|

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
    "vertical_strategy": "lines", 
    "horizontal_strategy": "lines",
    "explicit_vertical_lines": [],
    "explicit_horizontal_lines": [],
    "snap_tolerance": 3,
    "snap_x_tolerance": 3,
    "snap_y_tolerance": 3,
    "join_tolerance": 3,
    "join_x_tolerance": 3,
    "join_y_tolerance": 3,
    "edge_min_length": 3,
    "min_words_vertical": 3,
    "min_words_horizontal": 1,
    "keep_blank_chars": False,
    "text_tolerance": 3,
    "text_x_tolerance": 3,
    "text_y_tolerance": 3,
    "intersection_tolerance": 3,
    "intersection_x_tolerance": 3,
    "intersection_y_tolerance": 3,
}
```

| Setting | Description |
|---------|-------------|
|`"vertical_strategy"`| Either `"lines"`, `"lines_strict"`, `"text"`, or `"explicit"`. See explanation below.|
|`"horizontal_strategy"`| Either `"lines"`, `"lines_strict"`, `"text"`, or `"explicit"`. See explanation below.|
|`"explicit_vertical_lines"`| A list of vertical lines that explicitly demarcate cells in the table. Can be used in combination with any of the strategies above. Items in the list should be either numbers — indicating the `x` coordinate of a line the full height of the page — or `line`/`rect`/`curve` objects.|
|`"explicit_horizontal_lines"`| A list of horizontal lines that explicitly demarcate cells in the table. Can be used in combination with any of the strategies above. Items in the list should be either numbers — indicating the `y` coordinate of a line the full height of the page — or `line`/`rect`/`curve` objects.|
|`"snap_tolerance"`, `"snap_x_tolerance"`, `"snap_y_tolerance"`| Parallel lines within `snap_tolerance` pixels will be "snapped" to the same horizontal or vertical position.|
|`"join_tolerance"`, `"join_x_tolerance"`, `"join_y_tolerance"`| Line segments on the same infinite line, and whose ends are within `join_tolerance` of one another, will be "joined" into a single line segment.|
|`"edge_min_length"`| Edges shorter than `edge_min_length` will be discarded before attempting to reconstruct the table.|
|`"min_words_vertical"`| When using `"vertical_strategy": "text"`, at least `min_words_vertical` words must share the same alignment.|
|`"min_words_horizontal"`| When using `"horizontal_strategy": "text"`, at least `min_words_horizontal` words must share the same alignment.|
|`"intersection_tolerance"`, `"intersection_x_tolerance"`, `"intersection_y_tolerance"`| When combining edges into cells, orthogonal edges must be within `intersection_tolerance` pixels to be considered intersecting.|
|`"text_*"`| All settings prefixed with `text_` are then used when extracting text from each discovered table. All possible arguments to `Page.extract_text(...)` are also valid here.|
|`"text_x_tolerance"`, `"text_y_tolerance"`| These `text_`-prefixed settings *also* apply to the table-identification algorithm when the `text` strategy is used. I.e., when that algorithm searches for words, it will expect the individual letters in each word to be no more than `text_[x|y]_tolerance` pixels apart.|

### Table-extraction strategies

Both `vertical_strategy` and `horizontal_strategy` accept the following options:

| Strategy | Description | 
|----------|-------------|
| `"lines"` | Use the page's graphical lines — including the sides of rectangle objects — as the borders of potential table-cells. |
| `"lines_strict"` | Use the page's graphical lines — but *not* the sides of rectangle objects — as the borders of potential table-cells. |
| `"text"` | For `vertical_strategy`: Deduce the (imaginary) lines that connect the left, right, or center of words on the page, and use those lines as the borders of potential table-cells. For `horizontal_strategy`, the same but using the tops of words. |
| `"explicit"` | Only use the lines explicitly defined in `explicit_vertical_lines` / `explicit_horizontal_lines`. |

### Notes

- Often it's helpful to crop a page — `Page.crop(bounding_box)` — before trying to extract the table.

- Table extraction for `pdfplumber` was radically redesigned for `v0.5.0`, and introduced breaking changes.


## Extracting form values

Sometimes PDF files can contain forms that include inputs that people can fill out and save. While values in form fields appear like other text in a PDF file, form data is handled differently. If you want the gory details, see page 671 of this [specification](https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdf_reference_archive/pdf_reference_1-7.pdf).

`pdfplumber` doesn't have an interface for working with form data, but you can access it using `pdfplumber`'s wrappers around `pdfminer`.

For example, this snippet will retrieve form field names and values and store them in a dictionary. You may have to modify this script to handle cases like nested fields (see page 676 of the specification).

```python
pdf = pdfplumber.open("document_with_form.pdf")

fields = pdf.doc.catalog["AcroForm"].resolve()["Fields"]

form_data = {}

for field in fields:
    field_name = field.resolve()["T"]
    field_value = field.resolve()["V"]
    form_data[field_name] = field_value
```


## Demonstrations

- [Using `extract_table` on a California Worker Adjustment and Retraining Notification (WARN) report](examples/notebooks/extract-table-ca-warn-report.ipynb). Demonstrates basic visual debugging and table extraction.
- [Using `extract_table` on the FBI's National Instant Criminal Background Check System PDFs](examples/notebooks/extract-table-nics.ipynb). Demonstrates how to use visual debugging to find optimal table extraction settings. Also demonstrates `Page.crop(...)` and `Page.extract_text(...).`
- [Inspecting and visualizing `curve` objects](examples/notebooks/ag-energy-roundup-curves.ipynb).
- [Extracting fixed-width data from a San Jose PD firearm search report](examples/notebooks/san-jose-pd-firearm-report.ipynb), an example of using `Page.extract_text(...)`.

## Comparison to other libraries

Several other Python libraries help users to extract information from PDFs. As a broad overview, `pdfplumber` distinguishes itself from other PDF processing libraries by combining these features:

- Easy access to detailed information about each PDF object
- Higher-level, customizable methods for extracting text and tables
- Tightly integrated visual debugging
- Other useful utility functions, such as filtering objects via a crop-box

It's also helpful to know what features `pdfplumber` does __not__ provide:

- PDF *generation*
- PDF *modification*
- Optical character recognition (OCR)
- Strong support for extracting tables from OCR'ed documents

### Specific comparisons

- [`pdfminer.six`](https://github.com/pdfminer/pdfminer.six) provides the foundation for `pdfplumber`. It primarily focuses on parsing PDFs, analyzing PDF layouts and object positioning, and extracting text. It does not provide tools for table extraction or visual debugging.

- [`PyPDF2`](https://github.com/mstamy2/PyPDF2) is a pure-Python library "capable of splitting, merging, cropping, and transforming the pages of PDF files. It can also add custom data, viewing options, and passwords to PDF files." It can extract page text, but does not provide easy access to shape objects (rectangles, lines, etc.), table-extraction, or visually debugging tools.

- [`pymupdf`](https://pymupdf.readthedocs.io/) is substantially faster than `pdfminer.six` (and thus also `pdfplumber`) and can generate and modify PDFs, but the library requires installation of non-Python software (MuPDF). It also does not enable easy access to shape objects (rectangles, lines, etc.), and does not provide table-extraction or visual debugging tools.

- [`camelot`](https://github.com/camelot-dev/camelot), [`tabula-py`](https://github.com/chezou/tabula-py), and [`pdftables`](https://github.com/drj11/pdftables) all focus primarily on extracting tables. In some cases, they may be better suited to the particular tables you are trying to extract.


## Acknowledgments / Contributors

Many thanks to the following users who've contributed ideas, features, and fixes:

- [Jacob Fenton](https://github.com/jsfenfen)
- [Dan Nguyen](https://github.com/dannguyen)
- [Jeff Barrera](https://github.com/jeffbarrera)
- [Bob Lannon](https://github.com/boblannon)
- [Dustin Tindall](https://github.com/dustindall)
- [@yevgnen](https://github.com/Yevgnen)
- [@meldonization](https://github.com/meldonization)
- [Oisín Moran](https://github.com/OisinMoran)
- [Samkit Jain](https://github.com/samkit-jain)
- [Francisco Aranda](https://github.com/frascuchon)
- [Kwok-kuen Cheung](https://github.com/cheungpat)
- [Marco](https://github.com/ubmarco)
- [Idan David](https://github.com/idan-david)
- [@xv44586](https://github.com/xv44586)
- [Alexander Regueiro](https://github.com/alexreg)
- [Daniel Peña](https://github.com/trifling)
- [@bobluda](https://github.com/bobluda)
- [@ramcdona](https://github.com/ramcdona)
- [@johnhuge](https://github.com/johnhuge)
- [Jhonatan Lopes](https://github.com/jhonatan-lopes)
- [Ethan Corey](https://github.com/ethanscorey)
- [Shannon Shen](https://github.com/lolipopshock)
- [Matsumoto Toshi](https://github.com/toshi1127)
- [John West](https://github.com/jwestwsj)

## Contributing

Pull requests are welcome, but please submit a proposal issue first, as the library is in active development.

Current maintainers:

- [Jeremy Singer-Vine](https://github.com/jsvine)
- [Samkit Jain](https://github.com/samkit-jain)
