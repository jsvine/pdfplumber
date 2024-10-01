__all__ = [
    "__version__",
    "utils",
    "open",
    "repair",
    "set_debug",
]

from . import utils
from ._version import __version__
from .pdf import PDF
from .repair import repair

open = PDF.open
