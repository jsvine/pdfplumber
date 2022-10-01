.PHONY: venv tests check-black check-flake lint format examples
PYTHON := venv/bin/python
PIP = venv/bin/pip

venv:
	python3 -m venv venv
	${PIP} install --upgrade pip
	${PIP} install -r requirements.txt
	${PIP} install -r requirements-dev.txt
	${PIP} install -e .

tests:
	${PYTHON} -m pytest
	${PYTHON} -m coverage html

check-black:
	${PYTHON} -m black --check pdfplumber tests

check-isort:
	${PYTHON} -m isort --profile black --check-only pdfplumber tests

check-flake:
	${PYTHON} -m flake8 pdfplumber tests

check-mypy:
	${PYTHON} -m mypy --strict pdfplumber

lint: check-flake check-mypy check-black check-isort

format:
	${PYTHON} -m black pdfplumber tests
	${PYTHON} -m isort --profile black pdfplumber tests

examples:
	${PYTHON} -m nbexec.cli examples/notebooks

build:
	${PYTHON} -m build
