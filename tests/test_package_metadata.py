import runpy
from pathlib import Path
from unittest.mock import patch


def test_python_requirement_matches_classifiers():
    setup_path = Path(__file__).resolve().parents[1] / "setup.py"
    with patch("setuptools.setup") as setup:
        runpy.run_path(str(setup_path))
    requirement = setup.call_args.kwargs["python_requires"]
    classifiers = setup.call_args.kwargs["classifiers"]
    versions = [
        item.rsplit(" :: ", 1)[-1]
        for item in classifiers
        if item.startswith("Programming Language :: Python :: ")
    ]
    minimum = min(tuple(map(int, version.split("."))) for version in versions)

    assert requirement == f">={minimum[0]}.{minimum[1]}"
