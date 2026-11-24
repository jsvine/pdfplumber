from pathlib import Path
from runpy import run_path
from unittest.mock import patch


def test_python_requirement_matches_classifiers():
    with patch("setuptools.setup") as setup:
        run_path(str(Path(__file__).resolve().parents[1] / "setup.py"))
    metadata = setup.call_args.kwargs
    prefix = "Programming Language :: Python :: "
    versions = [
        tuple(map(int, classifier.removeprefix(prefix).split(".")))
        for classifier in metadata["classifiers"]
        if classifier.startswith(prefix)
    ]
    minimum = ".".join(map(str, min(versions)))
    assert metadata["python_requires"] == f">={minimum}"
