# Building these docs

The documentation is a [Sphinx](https://www.sphinx-doc.org) site written in Markdown
([MyST](https://myst-parser.readthedocs.io)) with the
[PyData theme](https://pydata-sphinx-theme.readthedocs.io). Its source is in `docs_sphinx/`.

## Build

From the repository root:

```sh
uv sync --group docs                                  # Sphinx, MyST, the theme and extensions
uv run sphinx-build -b html docs_sphinx/source docs_sphinx/build/html
```

Then open `docs_sphinx/build/html/index.html`. Or, from `docs_sphinx/`:

```sh
uv run make html          # same build
uv run make livehtml      # live preview at http://127.0.0.1:8000, rebuilt on every save
uv run make clean         # start over
```

Add `-W --keep-going` to `sphinx-build` (or `SPHINXOPTS="-W --keep-going"` to `make`) to
turn warnings, such as a broken cross-reference, into errors.

## Layout

| Path | Contents |
|---|---|
| `source/index.md` | Landing page and the top-level table of contents |
| `source/getting-started/` | Overview, installation, quick start, walkthrough, main window |
| `source/interface/` | Toolbar, stackup window, board panel, 3D view, shortcuts, log |
| `source/dc/`, `ac/`, `noise/`, `si/` | One section per analysis mode: concepts, setup, solving, results |
| `source/workflows.md` | Step-by-step workflows |
| `source/theory/` | The Solver Guide: PI background and how the solvers work |
| `source/reference/` | Files, troubleshooting, glossary, changelog, research notes |
| `source/development/` | Development, codebase layout, these build notes, license |
| `source/_static/custom.css` | Theme tweaks (tables, SVG diagrams, equations) |

Each folder has an `index.md` whose `toctree` lists its pages in order; a new page must be
added there to appear in the navigation.

## Shared files

Some content is not copied into `docs_sphinx/` but read from the rest of the repository, so
there is one copy to maintain:

- **Screenshots**: `docs/images/` is copied to `source/images/` on every build (that copy is
  git-ignored). Refer to an image as `/images/<name>.png`.
- **Changelog** and **research notes**: included from `docs/CHANGELOG.md` and
  `docs/research.md`.
- **Version**: read from `kipi_si/__init__.py`.

The offline `docs/help.html` (opened by KiPI-SI's **Help** button) and `docs/solver-guide.html`
are still separate files. When you change a feature, update both the HTML guide and the
matching page here.

## Writing tips

- Cross-reference a section by its label: `` {ref}`text <dc-loads>` ``. Labels are written
  as `(dc-loads)=` on the line before a heading. A page: `` {doc}`/dc/setup` ``.
- Notes and warnings: `:::{tip}` … `:::`, `:::{warning}` … `:::`.
- PASS/FAIL badges: `` {bdg-success}`PASS` ``, `` {bdg-danger}`FAIL` ``.
- Keys: `` {kbd}`Ctrl+1` ``.
