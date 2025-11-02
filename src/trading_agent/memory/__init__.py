"""Compatibility layer for legacy imports of the Memory module."""

from Memory import *  # noqa: F401,F403

# Re-export the version string if present for backward compatibility
try:  # pragma: no cover - defensive
    from Memory import __version__ as _version
except ImportError:  # pragma: no cover
    _version = "0.0.0"

__version__ = _version

__all__ = [name for name in globals() if not name.startswith("_")]
