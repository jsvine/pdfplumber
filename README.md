# PDFPlumber

Plumb a PDF for detailed information about each text character, rectangle, and line. Plus: Easily extract data from tables trapped in PDFs.

Works best on machine-generated, rather than scanned, PDFs. Built on [`pdfminer`](https://github.com/euske/pdfminer) and [`pdfminer.six`](https://github.com/goulu/pdfminer).

- [Installation](#installation)
- [Command Line Interface](#command-line-interface)
- [Python Library](#python-library)
- [Extracting tables](#extracting-tables)
- [Demos](#demos)

## Installation

```sh
pip install pdfplumber
```

## Command Line Interface

### Basic Example

```sh
curl "https://cdn.rawgit.com/jsvine/pdfplumber/master/examples/pdfs/background-checks.pdf" > background-checks.pdf
pdfplumber < background-checks.pdf > background-checks.csv
```

The output will be a CSV containing info about every character, line, and rectangle in the PDF.

### Options

- `--format [format]`: `csv` or `json`
    - The `json` format returns slightly more information; it includes PDF-level metadata and height/width information about each page.
- `--pages [list of pages]`: A space-delimited, `1`-indexed list of pages or hyphenated page ranges. E.g., `1, 11-15`, which would return data for pages 1, 11, 12, 13, 14, and 15.
- `--types [list of object types to extract]`: Choices are `char`, `anno`, `line`, `rect`, `rect_edge`. Defaults to `char`, `anno`, `line`, `rect`.

## Python Library

### Basic Example

```python
import pdfplumber

pdf = pdfplumber.from_path("path/to/file.pdf")
first_page = pdf.pages[0]

print(first_page.chars[0])
```

### Loading a PDF

`pdfplumber` provides two main ways to load a PDF:

- `pdfplumber.load(file_like_object)`

- `pdfplumber.from_path("path/to/file.pdf")`

Both methods return an instance of the `pdfplumber.PDF` class.

### The `pdfplumber.PDF` class

The top-level `pdfplumber.PDF` class represents a single PDF and has two main properties:

- `.metadata`: A dictionary of metadata key/value pairs, drawn from the PDF's `Info` trailers. Typically includes "CreationDate," "ModDate," "Producer," et cetera.

- `.pages`: A list containing one `pdfplumber.Page` instance per page loaded.

### The `pdfplumber.Page` class

The `pdfplumber.Page` class is at the core of `pdfplumber`. Most things you'll do with `pdfplumber` will revolve around this class. It has these main methods and properties:

- `.pageid`: The internal ID assigned to this page. Often, this number will correspond to the page number, but not necessarily.

- `.width`: The page's width.

- `.height`: The page's height.

- `.objects` / `.chars` / `.lines` / `.rects`: Each of these properties is a list, and each list contains one dictionary for each such object embedded on the page. For more detail, see "[Objects](#objects)" below.

- `.crop(bounding_box, strict=False)`: Returns a version of the page cropped to the bounding box, which should be expressed as 4-tuple with the values `(x0, top, x1, bottom)`.
    - By default, the cropped page retains objects that fall at least partly within the bounding box. If an object falls only partly within the box, its dimensions are sliced to fit the bounding box.
    - Calling `.crop` with `strict=True`, however, retains only objects that fall *entirely* within the bounding box.

- `.extract_text(x_tolerance=0, y_tolerance=0)`: Collates all of the page's character objects into a single string. Adds spaces where the difference between the `x1` of one character and the `x0` of the next is greater than `x_tolerance`. Adds newline characters where the difference between the `doctop` of one character and the `doctop` of the next is greater than `y_tolerance`.

- `.extract_table(...)`: Extracts tabular data from the page. For more details see "[Extracting tables](#extracting-tables)" below.

### Objects

Each instance of `pdfplumber.PDF` and `pdfplumber.Page` provides access to four types of PDF objects. The following properties each return a Python list of the matching objects:

- `.chars`, each representing a single text character.
- `.annos`, each representing a single annotation-text character.
- `.lines`, each representing a single 1-dimensional line.
- `.rects`, each representing a single 2-dimensional rectangle.

Each object is represented as a simple Python `dict`, with the following properties:

- `char` / `anno`:
    - `pageid`: Page ID on which this character was found.
    - `text`: E.g., "z", or "Z" or " ".
    - `fontname`: Name of the character's font face.
    - `size`: Font size.
    - `adv`: Equal to text width * the font size * scaling factor.
    - `upright`: Whether the character is upright.
    - `height`: Height of the character.
    - `width`: Width of the character.
    - `x0`: Distance of left side of character from left side of page.
    - `x1`: Distance of right side of character from left side of page.
    - `y0`: Distance of bottom of character from bottom of page.
    - `y1`: Distance of top of character from bottom of page.
    - `top`: Distance of top of character from top of page.
    - `bottom`: Distance of bottom of the character from top of page.
    - `doctop`: Distance of top of character from top of document.
    - `object_type`: "char" / "anno"

- `line`:
    - `pageid`: Page ID on which this line was found.
    - `height`: Height of line.
    - `width`: Width of line.
    - `x0`: Distance of left-side extremity from left side of page.
    - `x1`: Distance of right-side extremity from left side of page.
    - `y0`: Distance of bottom extremity from bottom of page.
    - `y1`: Distance of top extremity bottom of page.
    - `top`: Distance of top of line from top of page.
    - `bottom`: Distance of bottom of the line from top of page.
    - `doctop`: Distance of top of line from top of document.
    - `linewidth`: Thickness of line.
    - `object_type`: "line"

- `rect`:
    - `pageid`: Page ID on which this rectangle was found.
    - `height`: Height of rectangle.
    - `width`: Width of rectangle.
    - `x0`: Distance of left side of rectangle from left side of page.
    - `x1`: Distance of right side of rectangle from left side of page.
    - `y0`: Distance of bottom of rectangle from bottom of page.
    - `y1`: Distance of top of rectangle from bottom of page.
    - `top`: Distance of top of rectangle from top of page.
    - `bottom`: Distance of bottom of the rectangle from top of page.
    - `doctop`: Distance of top of rectangle from top of document.
    - `linewidth`: Thickness of line.
    - `object_type`: "rect"

Additionally, both `pdfplumber.PDF` and `pdfplumber.Page` provide access to two derived lists of objects: `.rect_edges` (which decomposes each rectangle into its four lines) and `.edges` (which combines `.rect_edges` with `.lines`). 

## Extracting Tables

You can think of `Page.extract_table(...)` as a sort of scriptable [Tablula](http://tabula.technology/). Given a page or cropped page, this method will return a list of lists representing the extracted table. By default, `extract_table` uses the page's vertical and horizontal lines (or rectangle edges) as cell-separators. But the method is highly customizable via these keyword arguments:

- `v=[strategy_name]`: Strategy for locating vertical dividers. Defaults to "lines," which uses lines and rectangle edges. Other options: "lines_strict," which only uses lines (and not rectangle edges), and "gutters," which looks for vertical sections of the document with no text in them.

- `h=[strategy_name]`: Strategy for locating horizontal dividers. Same defaults/options as `v`.

- `line_min_height=[number]`: The minimum height a line must be before being used in the vertical "lines" strategy. Defaults to `1`.

- `line_min_width=[number]`: The minimum width a line must be before being used in the horizontal "lines" strategy. Defaults to `1`.

- `gutter_min_width=[number]`: Minimum size of a character "gutter" to be used in the horizontal "gutters" strategy. Defaults to `5`.

- `gutter_min_height=[number]`: Minimum size of a character "gutter" to be used in the vertical "gutters" strategy. Defaults to `5`.

- `x_tolerance=[number]`: The maximum horizontal distance between two consecutive characters to consider them part of the same word. (Otherwise, a space is inserted between them.) Defaults to `0`.

- `x_tolerance=[number]`: The maximum vertical distance between two consecutive characters to consider them part of the same line. (Otherwise, a newline is inserted between them.) Defaults to `0`.

Note: Often it's helpful to crop a page before trying to extract the table. See the first demo below for an example.

## Demos

- [Use `extract_table` on the FBI's National Instant Criminal Background Check System PDFs.](examples/notebooks/extract-table-nics.ipynb)

## Python Support

Support for Python 3 is decent, but rough around the edges and largely dependent on the progress of [`pdfminer.six`](https://github.com/goulu/pdfminer).

Currently [tested](tests/) on [Python 2.7, 3.1, 3.3, 3.4, and 3.5](tox.ini).

## Acknowledgments / Contributors

Special thanks to [Jacob Fenton](https://github.com/jsfenfen).

## Feedback

Issues and pull requests welcome.
