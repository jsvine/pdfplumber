import pdfplumber
import pandas as pd
import argparse
from itertools import chain
import json
import sys

def parse_page_spec(p_str):
    if "-" in p_str:
        return list(range(*map(int, p_str.split("-"))))
    else: return [ int(p_str) ]

def parse_args():
    parser = argparse.ArgumentParser("pdfplumber")

    stdin = (sys.stdin.buffer if sys.version_info[0] >= 3 else sys.stdin)
    parser.add_argument("infile", nargs="?",
        type=argparse.FileType("rb"),
        default=stdin)

    parser.add_argument("--format",
        choices=["csv", "json"],
        default="csv")

    parser.add_argument("--types", nargs="+",
        choices=[ "char", "anno", "line", "rect", "image", "figure" ],
        default=[ "char", "anno", "line", "rect" ])

    parser.add_argument("--pages", nargs="+",
        type=parse_page_spec)

    args = parser.parse_args()
    if args.pages != None:
        args.pages = list(chain(*args.pages))
    return args

def to_csv(pdf, types):
    data = pd.concat([ pd.DataFrame(getattr(pdf, t + "s"))
        for t in types ])

    first_columns = [
        "object_type", "pageid",
        "x0", "x1", "y0", "y1",
        "top", "doctop",
        "width", "height"
    ]

    cols = first_columns + list(sorted(set(data.columns) - set(first_columns)))
    
    data[cols].to_csv(sys.stdout, index=False, encoding="utf-8")

def to_json(pdf, types):
    data = dict((t + "s", getattr(pdf, t + "s"))
        for t in types)
    json.dump(data, sys.stdout)

def main():
    args = parse_args()
    pdf = pdfplumber.load(args.infile, pages=args.pages)
    if args.format == "csv":
        to_csv(pdf, args.types)
    else:
        to_json(pdf, args.types)

if __name__ == "__main__":
    main()
