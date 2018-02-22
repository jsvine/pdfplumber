import sys, os
from setuptools import setup, find_packages
import subprocess

NAME = "pdfplumber"
HERE = os.path.abspath(os.path.dirname(__file__))
version_ns = {}

with open(os.path.join(HERE, NAME, "_version.py")) as f:
    exec(f.read(), {}, version_ns)

with open(os.path.join(HERE, "requirements.txt")) as f:
    base_reqs = f.read().strip().split("\n")

setup(
    name=NAME,
    description="Plumb a PDF for detailed information about each char, rectangle, and line.",
    version=version_ns['__version__'],
    packages=find_packages(exclude=["test",]),
    tests_require=[ "nose", "pandas" ] + base_reqs,
    install_requires=base_reqs,
    entry_points={
        "console_scripts": [ "pdfplumber = pdfplumber.cli:main" ] 
    }
)
