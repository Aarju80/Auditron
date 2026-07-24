"""
parser — public re-export surface for the parser sub-package.

Import from here to avoid coupling callers to internal module paths:

    from app.parser import parse_html, ParseResult
"""

from .parse import ParseResult, parse_html

__all__ = ["ParseResult", "parse_html"]
