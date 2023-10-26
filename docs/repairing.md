# Repairing Malformed PDFs

Many parsing issues can be traced back to malformed PDFs.

Malformed PDFs can often be [fixed via Ghostscript](https://superuser.com/questions/278562/how-can-i-fix-repair-a-corrupted-pdf-file).

`pdfplumber` lets you automatically run those repairs, in several ways:

- `pdfplumber.open(..., repair=True)` will repair your PDF on the fly (but not save the repaired version to disk).
- `pdfplumber.repair(path_to_pdf)` will return a `BytesIO` object holding the bytes of a repaired version of the original file.
- `pdfplumber.repair(path_to_pdf, outfile="path/to/repaired.pdf")` will write a repaired version of the original file to the indicated `outfile` path.

## Custom parameters

- `gs_path=...`: You can pass a custom path for the Ghostscript executable, helpful in case `pdfplumber` is unable to auto-detect your copy of Ghostscript.
