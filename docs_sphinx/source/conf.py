# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import re
import shutil
from pathlib import Path

DOCS_DIR = Path(__file__).parent.resolve()  # docs_sphinx/source
REPO = DOCS_DIR.parent.parent  # repository root


def _version():
    text = (REPO / "kipi_si" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    return m.group(1) if m else "unknown"


# -- Project information -----------------------------------------------------

project = "KiPI-SI"
copyright = "%Y, Drew Maatman (KiPI) and the KiPI-SI contributors"
author = "KiPI-SI contributors"
release = _version()
version = release


# -- Shared assets -----------------------------------------------------------
# The screenshots live in docs/images, next to the offline help.html that KiPI-SI's
# Help button opens. They are copied into the Sphinx source tree on every build
# (git-ignored), so there is one copy to keep up to date.


def _copy_assets(app):
    shutil.copytree(REPO / "docs" / "images", DOCS_DIR / "images", dirs_exist_ok=True)


def setup(app):
    app.connect("builder-inited", _copy_assets)


# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
]


myst_enable_extensions = [
    "colon_fence",  # ::: fences for admonitions and grids
    "deflist",
    "attrs_inline",
    "substitution",
]
myst_heading_anchors = 3  # [text](#heading-slug) links, as on GitHub
myst_substitutions = {"release": release}

source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]

copybutton_prompt_text = r"\$ |PS> "
copybutton_prompt_is_regexp = True


# -- HTML output -------------------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_title = f"KiPI-SI {release}"
html_logo = "../../resources/kipi_si_logo.svg"
html_favicon = "../../resources/kipi_si_48.png"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_theme_options = {
    "logo": {"text": "KiPI-SI"},
    "navigation_depth": 3,
    "show_toc_level": 2,
    "show_nav_level": 1,
    "header_links_before_dropdown": 6,
    "navbar_align": "left",
    "use_edit_page_button": True,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/MohamoudAli12/KiPI-SI",
            "icon": "fa-brands fa-github",
        }
    ],
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version"],
}
html_context = {
    "github_user": "MohamoudAli12",
    "github_repo": "KiPI-SI",
    "github_version": "main",
    "doc_path": "docs_sphinx/source",
}
# Pages that are short enough not to need the right-hand "On this page" bar.
html_sidebars = {
    "index": [],
}
