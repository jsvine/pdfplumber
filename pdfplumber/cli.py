#!/usr/bin/env python
import argparse
import json
import sys
from itertools import chain
from typing import List

from .pdf import PDF


def parse_page_spec(p_str: str) -> List[int]:
    if "-" in p_str:
        start, end = map(int, p_str.split("-"))
        return list(range(start, end + 1))
    else:
        return [int(p_str)]


def parse_args(args_raw: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser("pdfplumber")

    parser.add_argument(
        "infile", nargs="?", type=argparse.FileType("rb"), default=sys.stdin.buffer
    )

    parser.add_argument("--format", choices=["csv", "json"], default="csv")

    parser.add_argument("--types", nargs="+")

    parser.add_argument(
        "--include-attrs",
        nargs="+",
        help="Include *only* these object attributes in output.",
    )

    parser.add_argument(
        "--exclude-attrs",
        nargs="+",
        help="Exclude these object attributes from output.",
    )

    parser.add_argument("--laparams", type=json.loads)

    parser.add_argument("--precision", type=int)

    parser.add_argument("--pages", nargs="+", type=parse_page_spec)

    parser.add_argument(
        "--indent", type=int, help="Indent level for JSON pretty-printing."
    )

    args = parser.parse_args(args_raw)
    if args.pages is not None:
        args.pages = list(chain(*args.pages))
    return args


def main(args_raw: List[str] = sys.argv[1:]) -> None:
    args = parse_args(args_raw)

    with PDF.open(args.infile, pages=args.pages, laparams=args.laparams) as pdf:
        if args.format == "csv":
            pdf.to_csv(
                sys.stdout,
                args.types,
                precision=args.precision,
                include_attrs=args.include_attrs,
                exclude_attrs=args.exclude_attrs,
            )
        else:
            pdf.to_json(
                sys.stdout,
                args.types,
                precision=args.precision,
                include_attrs=args.include_attrs,
                exclude_attrs=args.exclude_attrs,
                indent=args.indent,
            )


if __name__ == "__main__":
    main()
