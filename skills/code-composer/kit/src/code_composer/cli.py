"""Compatibility shim for the legacy CLI module path."""
from .app.cli import main

__all__ = ["main"]

if __name__ == "__main__":
    main()
