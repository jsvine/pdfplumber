.PHONY: venv tests
PYTHON=venv/bin/python
PIP=venv/bin/pip

venv:
	python -m venv venv
	${PIP} install --upgrade pip
	${PIP} freeze --exclude-editable | xargs ${PIP} uninstall -y | true
	${PIP} install -r requirements.txt
	${PIP} install -r requirements-dev.txt
	${PIP} install -e .

tests:
	${PYTHON} -m pytest --cov=pdfplumber --cov-config=.coveragerc --cov-report xml:coverage.xml --cov-report term
