"""
validators — public re-export surface for the validation sub-package.

Import from here to avoid coupling callers to internal module paths:

    from app.validators import validate_url, UrlValidationResult
"""

from .url import UrlValidationResult, validate_url

__all__ = ["UrlValidationResult", "validate_url"]
