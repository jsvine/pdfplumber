import os

from setuptools import setup, find_packages

NAME = "pdfplumber"
HERE = os.path.abspath(os.path.dirname(__file__))

version_ns = {}


def _open(subpath):
    path = os.path.join(HERE, subpath)
    return open(path, encoding="utf-8")


with _open(NAME + "/_version.py") as f:
    exec(f.read(), {}, version_ns)

with _open("requirements.txt") as f:
    base_reqs = f.read().strip().split("\n")

with _open("requirements-dev.txt") as f:
    dev_reqs = f.read().strip().split("\n")

with _open("README.md") as f:
    long_description = f.read()

setup(
    name=NAME,
    url="https://github.com/jsvine/pdfplumber",
    author="Jeremy Singer-Vine",
    author_email="jsvine@gmail.com",
    description="Plumb a PDF for detailed information about each char, rectangle, and line.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version=version_ns["__version__"],
    packages=find_packages(
        exclude=[
            "test",
        ]
    ),
    include_package_data=True,
    package_data={"pdfplumber": ["py.typed"]},
    zip_safe=False,
    tests_require=base_reqs + dev_reqs,
    python_requires=">=3.7",
    install_requires=base_reqs,
    entry_points={"console_scripts": ["pdfplumber = pdfplumber.cli:main"]},
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
