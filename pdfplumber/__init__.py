from ._version import __version__
from . import utils
from . import edge_finders
from .pdf import PDF

import pdfminer
import pdfminer.pdftypes
import pdfminer.pdfinterp
pdfminer.pdftypes.STRICT = False
pdfminer.pdfinterp.STRICT = False

def load(file_or_buffer, **kwargs):
    return PDF(file_or_buffer, **kwargs)

open = PDF.open

# Old idiom
from_path = PDF.open 

def set_debug(debug=0):
    pdfminer.debug = debug

set_debug(0)
