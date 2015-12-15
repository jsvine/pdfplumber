import sys, os
from setuptools import setup, find_packages
import subprocess

base_reqs = [
    "chardet",
    "pycrypto",
    "pdfminer.six>=20151013"
]

setup(
    name="pdfplumber",
    version="0.0.2",
    packages=find_packages(exclude=["test",]),
    tests_require=[ "nose", "pandas>=0.17.1" ] + base_reqs,
    install_requires=base_reqs,
)
