.PHONY: venv tests check-black check-flake format
PYTHON := venv/bin/python
PIP = venv/bin/pip

venv:
	python -m venv venv
	${PIP} install --upgrade pip
	${PIP} install -r requirements.txt
	${PIP} install -r requirements-dev.txt
	${PIP} install -e .

tests:
	${PYTHON} -m pytest
	${PYTHON} -m coverage html

check-black:
	${PYTHON} -m black pdfplumber --check

check-flake:
	${PYTHON} -m flake8 pdfplumber

format:
	${PYTHON} -m black pdfplumber
