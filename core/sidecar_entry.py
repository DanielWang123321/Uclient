"""PyInstaller entry point (absolute import so the package context is preserved)."""

import sys

from uclient_core.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
