from inveniautils.version import __version__ as version
from setuptools import find_packages, setup

with open('requirements/install.txt') as f:
    requirements = f.read().splitlines()


setup(
    name="InveniaUtils",
    version=version,
    description="Miscellaneous Python code that doesn't belong in any one project.",
    author="Invenia Technical Computing",
    url="https://gitlab.invenia.ca/invenia/inveniautils",
    packages=find_packages(exclude=["tests"]),
    install_requires=requirements,
    include_package_data=True,
)
