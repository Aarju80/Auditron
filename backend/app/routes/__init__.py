"""
routes — public re-export surface for the routes sub-package.

Import from here to avoid coupling callers to internal module paths:

    from app.routes import audit_router
"""

from .audit import router as audit_router

__all__ = ["audit_router"]
