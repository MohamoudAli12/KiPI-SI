"""The standalone launcher: sets up KiPI-SI's own Python environment on first run, then starts
KiPI-SI in it.

Everything in this package runs on the Python that started the launcher, before any of
KiPI-SI's dependencies exist, so it uses the standard library only (``tests/core/test_layering.py``
checks). It also has to get far enough on an older Python to say which one KiPI-SI needs, so
it keeps to syntax Python 3.8 understands.
"""
