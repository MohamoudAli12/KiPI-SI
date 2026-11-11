# KiPI-SI documentation (Sphinx)

```sh
uv sync --group docs
uv run sphinx-build -b html docs_sphinx/source docs_sphinx/build/html
```

Open `docs_sphinx/build/html/index.html`. See `source/development/building-docs.md` for the
layout and writing tips.
