# KiPI-SI documentation (Sphinx)

```sh
uv sync --group docs
uv run sphinx-build -b html docs/source docs/build/html
```

Open `docs/build/html/index.html`. See `source/development/building-docs.md` for the
layout and writing tips. Pushes to `main` publish the site to
<https://mohamoudali12.github.io/KiPI-SI/>.
