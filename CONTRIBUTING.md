# Contribution Guidelines

Thank you for your interest in `pdfplumber`! Before submitting an issue or filing a pull request, please consult the brief notes and instructions below.

## Creating issues

- If you are __troubleshooting__ a specific PDF and have not identified a clear bug, please [open a discussion](https://github.com/jsvine/pdfplumber/discussions) instead of an issue. 
- Malformed PDFs can often cause problems that cannot be directly fixed in `pdfplumber`. For that reason, please __try repairing__ your PDF using [Ghostscript](https://www.ghostscript.com/) before filing a bug report. To do so, run `gs -o repaired.pdf -sDEVICE=pdfwrite original.pdf`, replacing `original.pdf` with your PDF's actual filename.
- If your issue relates to __text not being displayed__ correctly, please compare the output to [`pdfminer.six`'s `pdf2txt` command](https://pdfminersix.readthedocs.io/en/latest/tutorial/commandline.html). If you're seeing the same problems there, please consult that repository instead of this one, because `pdfplumber` depends on `pdfminer.six` for text extraction.
- Please do fill out all requested sections of the __issue template__; doing so will help the maintainers and community more efficiently respond.

## Submitting pull requests

- If you would like to propose a change that is more __complex__ than a simple bug-fix, please [first open a discussion](https://github.com/jsvine/pdfplumber/discussions). If you are submitting a __simple__ bugfix, typo correction, et cetera, feel free to open a pull request directly.
- PRs should be submitted against the __`develop` branch__ only.
- PRs should contain one or more __tests__ that support the changes. The tests should pass with the new code but fail on the commits prior. For guidance, see the existing tests in the `tests/` directory. To execute the tests, run `make tests` or `python -m pytest`.
- Python code in PRs should conform to [`psf/black`](https://black.readthedocs.io/en/stable/), [`isort`](https://pycqa.github.io/isort/index.html), and [`flake8`](https://pypi.org/project/flake8/) __formatting__ guidelines. To automatically reformat your code accordingly, run `make format`. To test the formatting and `flake8` compliance, run `make lint`.
- Please add yourself to the [list of contributors](https://github.com/jsvine/pdfplumber#acknowledgments--contributors).
- Please also update the [CHANGELOG.md](https://github.com/jsvine/pdfplumber/blob/develop/CHANGELOG.md).
