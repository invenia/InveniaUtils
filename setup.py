from os import path
from setuptools import find_packages, setup
import inveniautils

REQUIREMENTS = ['pytz', 'lxml', 'pint', 'python-dateutil', 'cryptography']

setup(
    name="InveniaUtils",
    version=inveniautils.__version__,
    description="Miscellaneous Python code that doesn't belong in any one project.",
    author="Ryan Froese",
    url="https://gitlab.invenia.ca/invenia/inveniautils",
    packages=find_packages(exclude=["tests"]),
    install_requires=REQUIREMENTS,
)
