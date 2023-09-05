#!/usr/bin/env python

"""Create an xref section for a simple handmade PDF.

Not a general purpose tool!!!"""

import re
import sys

with open(sys.argv[1], "rb") as infh:
    pos = 0
    xref = [(0, 65535, "f")]
    for spam in infh:
        text = spam.decode("ascii")
        if re.match(r"\s*(\d+)\s+(\d+)\s+obj", text):
            xref.append((pos, 0, "n"))
        elif text.strip() == "xref":
            startxref = pos
        pos = infh.tell()
    print("xref")
    print("0", len(xref))
    for x in xref:
        print("%010d %05d %s " % x)
    print("trailer  << /Size %d /Root 1 0 R >>" % len(xref))
    print("startxref")
    print(startxref)
    print("%%EOF")
