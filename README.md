__WARNING: This software is in its very early days, might not work well, and might change dramatically in future versions.__

# PDFPlumber

Plumb a PDF for detailed information about each text character, rectangle, line, and image.

Built on [`pdfminer`](https://github.com/euske/pdfminer) and [`pdfminer.six`](https://github.com/goulu/pdfminer).

## Installation

```sh
pip install pdfplumber
```

## Usage

### Basic Example

```python
import pdfplumber

pdf = pdfplumber.from_path("path/to/file.pdf")

if len(pdf.chars):
    print(pdf.chars[0])

if len(pdf.rects):
    print(pdf.rects[0])

if len(pdf.lines):
    print(pdf.lines[0])
```

### Loading a PDF

`pdfplumber` provides two main ways to load a PDF:

- `pdfplumber.load(file_like_object)`
- `pdfplumber.from_path("path/to/file.pdf")`

Both methods return an instance of the `pdfplumber.PDF` class.

### Objects

Each instance of `pdfplumber.PDF` provides access to six types of PDF objects. The following properties each return a Python list of the matching objects:

- `.chars`, each representing a single text character.
- `.annos`, each representing a single annotation-text character.
- `.lines`, each representing a single 1-dimensional line.
- `.rects`, each representing a single 2-dimensional rectangle.
- `.images`, each representing a single image.
- `.figures`, each representing a single figure.

### Object Properties

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
    - `doctop`: Distance of top of character from top of document.
    - `kind`: "LTChar" / "LTAnno"

- `line`:
    - `pageid`: Page ID on which this line was found.
    - `height`: Height of line.
    - `width`: Width of line.
    - `x0`: Distance of left-side extremity from left side of page.
    - `x1`: Distance of right-side extremity from left side of page.
    - `y0`: Distance of bottom extremity from bottom of page.
    - `y1`: Distance of top extremity bottom of page.
    - `top`: Distance of top of line from top of page.
    - `doctop`: Distance of top of line from top of document.
    - `linewidth`: Thickness of line.
    - `kind`: "LTLine"

- `rect`:
    - `pageid`: Page ID on which this rectangle was found.
    - `height`: Height of rectangle.
    - `width`: Width of rectangle.
    - `x0`: Distance of left side of rectangle from left side of page.
    - `x1`: Distance of right side of rectangle from left side of page.
    - `y0`: Distance of bottom of rectangle from bottom of page.
    - `y1`: Distance of top of rectangle from bottom of page.
    - `top`: Distance of top of rectangle from top of page.
    - `doctop`: Distance of top of rectangle from top of document.
    - `linewidth`: Thickness of line.
    - `kind`: "LTRect"

- `image`: TK

- `figure`: TK

## Python Support

Support for Python 3 is rough around the edges and largely dependent on the progress of [`pdfminer.six`](https://github.com/goulu/pdfminer).

## Feedback

Issues and pull requests welcome.
