__WARNING: This software is in its very early days, might not work well, and might change dramatically in future versions.__

# PDFPlumber

Plumb a PDF for detailed information about each char, rectangle, line, et cetera.

Built on [`pdfminer`](https://github.com/euske/pdfminer)/[`pdfminer.six`](https://github.com/goulu/pdfminer).

## Installation

```sh
pip install git+https://github.com/goulu/pdfminer#egg=pdfminer.six
pip install pdfplumber
```

## Usage

```python
import pdfplumber

pdf = pdfplumber.from_path("path/to/file.pdf")

# OR

with open("path/to/file.pdf") as f:
    pdf = pdfplumber.load(f)

print(pdf.chars)
print(pdf.rects)
print(pdf.lines)
```

### Pandas Integration

By default, `pdf.chars`, etc., will be a plain Python dictionary. But if you `pandas=True` to `pdfplumber.load`/`.from_file`, you'll receive those properties as [Pandas dataframes](http://pandas.pydata.org/pandas-docs/stable/dsintro.html#dataframe). 

## Python Support

Support for Python 3 is rough around the edges and largely dependent on the progress of [`pdfminer.six`](https://github.com/goulu/pdfminer).

## Feedback

Issues and pull requests welcome.
