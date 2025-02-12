import sys
from enum import IntEnum

import atheris
from fuzz_helpers import EnhancedFuzzedDataProvider

with atheris.instrument_imports(include=["pdfplumber"]):
    from pdfminer.pdftypes import PDFException
    from pdfminer.psparser import PSException
    from pdfplumber.utils.exceptions import MalformedPDFException, PdfminerException

    import pdfplumber


class CastType(IntEnum):
    CSV = 0
    IMAGE = 1
    JSON = 2
    DICT = 3
    MAX = 4


def TestOneInput(data: bytes):
    fdp = EnhancedFuzzedDataProvider(data)

    try:
        with fdp.ConsumeMemoryFile(all_data=False, as_bytes=True) as f:
            pdf = pdfplumber.open(f)

            # Test casting
            cast_ty = fdp.ConsumeEnum(CastType)

            if cast_ty is CastType.CSV:
                pdf.to_csv()
            elif cast_ty is CastType.IMAGE and pdf.pages:
                pdf.pages[0].to_image()
            elif cast_ty is CastType.JSON:
                pdf.to_json()
            elif cast_ty is CastType.DICT:
                pdf.to_dict()

    except (PDFException, PSException, AssertionError, MalformedPDFException, PdfminerException):
        return -1
    except ValueError as e:
        if "invalid literal for int" in str(e):
            return -1
        raise e
    except TypeError as e:
        if "argument must be a string" in str(e):
            return -1
        raise e


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
