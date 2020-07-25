.PHONY: venv tests
PYTHON=venv/bin/python
PIP=venv/bin/pip

venv:
	python -m venv venv
	${PIP} install -U pip
	${PIP} freeze | xargs ${PIP} uninstall -y
	${PIP} install -r requirements.txt
	${PIP} install -r requirements-dev.txt

tests:
	${PYTHON} -m pytest
