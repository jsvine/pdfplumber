#!/usr/bin/env python

"""Create an xref section for a simple handmade PDF.

Not a general purpose tool!!!"""

import re
import sys

with open(sys.argv[1], "r+b") as infh:
    pos = 0
    xref = [(0, 65535, "f")]
    for spam in infh:
        text = spam.decode("ascii")
        if re.match(r"\s*(\d+)\s+(\d+)\s+obj", text):
            xref.append((pos, 0, "n"))
        elif text.strip() == "xref":
            startxref = pos
        pos = infh.tell()
    infh.seek(startxref)
    infh.write(b"xref\n")
    infh.write(("0 %d\n" % len(xref)).encode("ascii"))
    for x in xref:
        infh.write(("%010d %05d %s \n" % x).encode("ascii"))
    infh.write(("trailer  << /Size %d /Root 1 0 R >>\n" % len(xref)).encode("ascii"))
    infh.write(b"startxref\n")
    infh.write(("%d\n" % startxref).encode("ascii"))
    infh.write(b"%%EOF\n")
