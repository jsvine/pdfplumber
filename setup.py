import sys, os
from setuptools import setup, find_packages
import subprocess

base_reqs = [
    "chardet",
    "pycrypto",
    "pandas>=0.17.1",
    "pdfminer.six>=20151013"
]

setup(
    name="pdfplumber",
    description="Plumb a PDF for detailed information about each char, rectangle, line, etc.",
    version="0.2.0",
    packages=find_packages(exclude=["test",]),
    tests_require=[ "nose" ] + base_reqs,
    install_requires=base_reqs,
    entry_points={
        "console_scripts": [ "pdfplumber = pdfplumber.cli:main" ] 
    }
)
