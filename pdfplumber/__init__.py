__all__ = [
    "__version__",
    "utils",
    "pdfminer",
    "open",
    "set_debug",
]

import sys

import pdfminer
import pdfminer.pdftypes

from . import utils
from ._version import __version__
from .pdf import PDF

pdfminer.pdftypes.STRICT = False
pdfminer.pdfinterp.STRICT = False

open = PDF.open


def load(file_or_buffer, **kwargs):
    sys.stderr.write(
        "Warning: pdfplumber.load is deprecated."
        "Please use pdfplumber.open (with same arguments) instead."
        "\n"
    )
    return PDF(file_or_buffer, **kwargs)


def set_debug(debug=0):
    pdfminer.debug = debug


set_debug(0)
