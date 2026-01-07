.PHONY: venv tests check-black check-flake lint format examples build
VENV ?= .venv
PYTHON = ${VENV}/bin/python

venv:
	python3 -m venv venv
	${VENV}/bin/pip install --upgrade pip
	${VENV}/bin/pip install -r requirements.txt
	${VENV}/bin/pip install -r requirements-dev.txt
	${VENV}/bin/pip install -e .

tests:
	${PYTHON} -m pytest -n auto
	${PYTHON} -m coverage html

check-black:
	${VENV}/bin/black --check pdfplumber tests

check-isort:
	${VENV}/bin/isort --profile black --check-only pdfplumber tests

check-flake:
	${VENV}/bin/flake8 pdfplumber tests

check-mypy:
	${VENV}/bin/mypy --strict --implicit-reexport pdfplumber

lint: check-flake check-mypy check-black check-isort

format:
	${VENV}/bin/black pdfplumber tests
	${VENV}/bin/isort --profile black pdfplumber tests

examples:
	${VENV}/bin/nbexec examples/notebooks

build:
	${PYTHON} -m build
