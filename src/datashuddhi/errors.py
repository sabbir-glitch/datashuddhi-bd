"""Exception types.

Privacy rule: exception messages must never contain scanned content or a matched value.
Messages are fixed strings (optionally with numbers or option names). Do not add
``str(original_exception)`` of operating-system errors, because those can contain paths.
"""

from __future__ import annotations


class DataShuddhiError(Exception):
    """Base class for all errors raised on purpose by this package."""


class ConfigError(DataShuddhiError, ValueError):
    """An option or limit has an invalid value (maps to exit code 2)."""


class InvalidScanRootError(DataShuddhiError):
    """The path to scan is missing, of the wrong type, or not supported (exit code 2)."""


class ScanFatalError(DataShuddhiError):
    """The scan cannot give a reliable result at all (exit code 3)."""
