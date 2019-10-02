from os import path

from setuptools import find_packages, setup


TEST_DEPS = ["coverage", "pytest", "pytest-cov"]
DOCS_DEPS = ["sphinx", "sphinx-rtd-theme", "sphinx-autoapi", "recommonmark"]
CHECK_DEPS = ["isort", "flake8", "flake8-quotes", "pep8-naming", "mypy", "black"]
REQUIREMENTS = ['pytz', 'lxml', 'pint', 'python-dateutil', 'cryptography']

EXTRAS = {
    "test": TEST_DEPS,
    "docs": DOCS_DEPS,
    "check": CHECK_DEPS,
    "dev": TEST_DEPS + DOCS_DEPS + CHECK_DEPS,
}

# Read in the version
with open(path.join(path.dirname(path.abspath(__file__)), "VERSION")) as version_file:
    version = version_file.read().strip()


setup(
    name="Invenia Utils",
    version=version,
    description="Miscellaneous Python code that doesn't belong in any one project.",
    author="Ryan Froese",
    url="https://gitlab.invenia.ca/invenia/inveniautils",
    packages=find_packages(exclude=["tests"]),
    install_requires=REQUIREMENTS,
    include_package_data=True,
    tests_require=TEST_DEPS,
    extras_require=EXTRAS,
)
