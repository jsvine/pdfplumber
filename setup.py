import sys, os
from setuptools import setup, find_packages
import subprocess

base_reqs = [
    "chardet",
    "pycrypto",
    "pdfminer.six"
]

setup(
    name="pdfplumber",
    version="0.0.1",
    packages=find_packages(exclude=["test",]),
    tests_require=[ "nose", "pandas" ] + base_reqs,
    install_requires=base_reqs,
)
