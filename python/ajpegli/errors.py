from __future__ import annotations


class AjpegliError(Exception):
    """Base exception for ajpegli failures."""


class DecodeError(AjpegliError):
    """Raised when JPEG decode or header parsing fails."""


class EncodeError(AjpegliError):
    """Raised when JPEG encode fails."""


class InvalidInputError(AjpegliError, ValueError):
    """Raised when Python inputs fail validation before native execution."""


class UnsupportedModeError(AjpegliError):
    """Raised when a colorspace, dtype, or mode is not supported."""


class MetadataError(AjpegliError):
    """Raised when metadata cannot be represented as JPEG markers."""


class SecurityError(AjpegliError):
    """Raised when input violates configured safety limits."""

