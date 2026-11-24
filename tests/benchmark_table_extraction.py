"""Measure Table.extract, excluding PDF parsing and table detection.

From the project root with pdfplumber installed:
    python tests/benchmark_table_extraction.py 5 250 750
"""

import argparse
from statistics import median
from time import perf_counter
from unittest.mock import Mock

from pdfplumber.page import Page
from pdfplumber.table import Table


def make_table(rows, columns=6):
    cells = []
    chars = []
    for row in range(rows):
        for column in range(columns):
            top, x0 = 12 * row, 42 * column
            cells.append((x0, top, x0 + 42, top + 12))
            for index, text in enumerate("ABC123"):
                x = x0 + index * 4 + 1
                chars.append(
                    {
                        "text": text,
                        "upright": True,
                        "size": 8,
                        "x0": x,
                        "x1": x + 4,
                        "top": top + 2,
                        "bottom": top + 10,
                        "doctop": top + 2,
                    }
                )
    return Table(Mock(spec=Page, chars=chars), cells)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=int, nargs="+")
    args = parser.parse_args()
    for rows in args.rows:
        table = make_table(rows)
        times = []
        for _ in range(3):
            start = perf_counter()
            actual = table.extract()
            times.append(perf_counter() - start)
            assert actual == [["ABC123"] * 6] * rows
        print(f"{rows} rows, {rows * 36} chars: {median(times):.4f} s")


if __name__ == "__main__":
    main()
