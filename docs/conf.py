# Configuration file for the Sphinx documentation builder.
import os
import sys

from inveniautils.version import __version__ as version

# Required for resolving imports within this package
sys.path.insert(0, os.path.abspath('../source'))

# -- Project information ---------------------------------------------------------------

project = 'InveniaUtils'
year = "2020"
author = "Invenia Technical Computing"
copyright = f"{year}, {author}"


# -- General configuration -------------------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
    "sphinx.ext.autodoc",
    # http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
    "sphinx.ext.napoleon",
    # http://www.sphinx-doc.org/en/master/usage/extensions/todo.html
    "sphinx.ext.todo",
    # http://www.sphinx-doc.org/en/master/usage/extensions/viewcode.html
    "sphinx.ext.viewcode",
    # https://sphinx-autoapi.readthedocs.io/en/latest/
    "autoapi.extension",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -----------------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_last_updated_fmt = "%b %d, %Y"
html_short_title = f"{project}-{version}"

# Pygments Style Settings
pygments_style = "monokai"

# Set initial page name
master_doc = "index"

# Sphinx Extension Autodoc -------------------------------------------------------------

# Order members by source order
autodoc_member_order = "bysource"

# Always show members, and member-inheritance by default
autodoc_default_flags = ["members", "show-inheritance"]


# Sphinx Extension Napoleon ------------------------------------------------------------

# We want to force google style docstrings, so disable numpy style
napoleon_numpy_docstring = False

# Set output style
napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False

# Sphinx Extension AutoAPI -------------------------------------------------------------
autoapi_type = "python"
autoapi_dirs = ["../inveniautils/"]
autoapi_ignore = ["*/inveniautils/version.py"]
autoapi_root = "autoapi"
autoapi_add_toctree_entry = False
autoapi_keep_files = False
