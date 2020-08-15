import sys, os
from setuptools import setup, find_packages
import subprocess

NAME = "pdfplumber"
HERE = os.path.abspath(os.path.dirname(__file__))

version_ns = {}
with open(os.path.join(HERE, NAME, '_version.py')) as f:
    exec(f.read(), {}, version_ns)

with open(os.path.join(HERE, "requirements.txt")) as f:
    base_reqs = f.read().strip().split("\n")

with open(os.path.join(HERE, "requirements-dev.txt")) as f:
    dev_reqs = f.read().strip().split("\n")

with open(os.path.join(HERE, "README.md")) as f:
    long_description = f.read()

setup(
    name=NAME,
    description="Plumb a PDF for detailed information about each char, rectangle, and line.",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    version=version_ns['__version__'],
    packages=find_packages(exclude=["test",]),
    tests_require = base_reqs + dev_reqs,
    install_requires = base_reqs,
    entry_points={
        "console_scripts": [ "pdfplumber = pdfplumber.cli:main" ] 
    },
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
