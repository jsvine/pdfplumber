class MalformedPDFException(Exception):
    pass


class PdfminerException(Exception):
    def __str__(self) -> str:
        msg = super().__str__()
        if not msg and self.args and isinstance(self.args[0], BaseException):
            # pdfminer.six raises some exceptions without a message (e.g.
            # PDFPasswordIncorrect), which would otherwise be surfaced here
            # as a blank error message.
            return type(self.args[0]).__name__
        return msg
