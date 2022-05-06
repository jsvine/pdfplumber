__all__ = [
    "__version__",
    "utils",
    "pdfminer",
    "open",
    "set_debug",
]

import pdfminer
import pdfminer.pdftypes

from . import utils
from ._version import __version__
from .pdf import PDF

open = PDF.open
