import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).parent))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx_toolbox.more_autodoc.autoprotocol",
    "sphinx_toolbox.more_autodoc.typevars",
    "sphinx_immaterial",
]

html_theme = "sphinx_immaterial"
html_static_path = ["_static"]
html_css_files = ["css/extra.css"]

html_theme_options = {
    "repo_url": "https://github.com/kraken-tech/django-consistency-enforcer",
    "features": ["toc.integrate", "navigation.tabs", "navigation.tabs.sticky"],
}

exclude_patterns = ["_build/**", ".sphinx-build/**", "README.rst"]

master_doc = "index"
source_suffix = ".rst"

pygments_style = "pastie"

copyright = "Kraken"
project = "django_consistency_enforcer"

version = "0.1"
release = "0.1"

autodoc_preserve_defaults = True
