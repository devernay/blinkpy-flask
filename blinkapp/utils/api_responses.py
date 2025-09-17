"""Utility functions for creating standardized API responses.

This module has been deprecated. Use blinkapp.models.responses.create_api_response instead.
"""

# Re-export the canonical version from models
from blinkapp.models.responses import create_api_response

__all__ = ["create_api_response"]
