"""
Exception hierarchy for the Codeforces API client.

Keeping errors in their own module lets callers (service layer, tool
wrappers, route handlers) import just what they need without circular
imports.
"""


class CFError(Exception):
    """Base exception for all Codeforces client errors."""


class CFHandleNotFound(CFError):
    """Raised when the CF API reports that a handle does not exist."""


class CFAPIError(CFError):
    """Raised for non-404 API errors (malformed response, server error, etc.)."""


class CFRateLimitError(CFAPIError):
    """Raised when the CF API returns HTTP 429."""
