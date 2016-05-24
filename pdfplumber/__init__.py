from pdfplumber.pdf import PDF
import pdfplumber.utils
import pdfminer
import pdfminer.pdftypes
pdfminer.pdftypes.STRICT = False
pdfminer.pdfinterp.STRICT = False

VERSION_TUPLE = (0, 4, 4)
VERSION = ".".join(map(str, VERSION_TUPLE))

def load(file_or_buffer, **kwargs):
    return PDF(file_or_buffer, **kwargs)

open = PDF.open
# Old idiom
from_path = PDF.open 

def set_debug(debug=0):
    pdfminer.debug = debug

set_debug(0)
