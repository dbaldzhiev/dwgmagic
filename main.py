"""Thin launcher kept for backwards compatibility.

The actual entrypoint lives in :mod:`dwgmagic.cli`; installed environments can
also use the ``dwgmagic`` console script provided by the package.
"""
from dwgmagic.cli import build_environment, main  # noqa: F401 - re-exported

if __name__ == "__main__":
    main()
