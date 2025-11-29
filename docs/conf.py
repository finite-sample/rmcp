# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "RMCP"
copyright = "2024, Gaurav Sood"
author = "Gaurav Sood"

# Get version from package
sys.path.insert(0, os.path.abspath(".."))
try:
    from rmcp.version import get_version

    version = get_version()
    release = get_version()
except ImportError:
    # Fallback if package not available
    version = "0.7.0"
    release = "0.7.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Source file parsers
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
html_title = f"RMCP {version} Documentation"

# Theme options for Furo
html_theme_options = {
    # Enable navigation with keyboard arrows
    "navigation_with_keys": True,
    # Show edit button on top of page (if source is available)
    "top_of_page_buttons": ["edit", "view"],
    # Light mode CSS variables for branding
    "light_css_variables": {
        "color-brand-primary": "#0066CC",
        "color-brand-content": "#0066CC",
        "font-stack": "-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif",
        "font-stack--monospace": "SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace",
    },
    # Dark mode CSS variables
    "dark_css_variables": {
        "color-brand-primary": "#4A9EFF",
        "color-brand-content": "#4A9EFF",
    },
    # Sidebar configuration
    "sidebar_hide_name": False,
}

# -- Extension configuration -------------------------------------------------

# autodoc
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
    "show-inheritance": True,
}
autodoc_typehints = "both"
autodoc_typehints_description_target = "documented"
autodoc_preserve_defaults = True

# autosummary
autosummary_generate = True
autosummary_generate_overwrite = True
autosummary_imported_members = False

# napoleon - for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "click": ("https://click.palletsprojects.com/en/8.1.x/", None),
}

# MyST parser configuration
myst_enable_extensions = [
    "deflist",
    "tasklist", 
    "colon_fence",
    "attrs_inline",
    "attrs_block",
    "fieldlist",
    "substitution",
    "dollarmath",
    "linkify",
]

# Enable including content from other files
myst_heading_anchors = 3
myst_fence_as_directive = ["note", "warning", "error"]

# autosectionlabel
autosectionlabel_prefix_document = True

# Copy button configuration
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True
