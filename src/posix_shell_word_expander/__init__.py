"""POSIX shell word expansion: splitting and quote removal without execution.

This package exposes :func:`expand` and :class:`ExpansionError`.
"""

from .core import ExpansionError, expand

__all__ = ["expand", "ExpansionError"]
