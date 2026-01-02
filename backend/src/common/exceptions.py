"""
Custom exception handling for consistent API error responses.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error responses.

    Response format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {...}  # Optional field-level errors
        }
    }
    """
    # Call default handler first
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            'error': {
                'code': _get_error_code(exc),
                'message': _get_error_message(exc, response),
                'details': _get_error_details(exc, response),
            }
        }
        response.data = error_payload

    # Handle Django ValidationError
    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Validation failed',
                    'details': exc.message_dict if hasattr(exc, 'message_dict') else {'__all__': exc.messages},
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Handle built-in Python exceptions that represent business logic errors
    if response is None:
        if isinstance(exc, (ValueError, TypeError)):
            return Response(
                {
                    'error': {
                        'code': 'INVALID_REQUEST',
                        'message': str(exc),
                        'details': None,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    return response


def _get_error_code(exc):
    """Map exception to error code."""
    from rest_framework.exceptions import (
        AuthenticationFailed,
        NotAuthenticated,
        NotFound,
        PermissionDenied,
        Throttled,
        ValidationError,
    )

    error_codes = {
        AuthenticationFailed: 'AUTHENTICATION_FAILED',
        NotAuthenticated: 'NOT_AUTHENTICATED',
        PermissionDenied: 'PERMISSION_DENIED',
        NotFound: 'NOT_FOUND',
        ValidationError: 'VALIDATION_ERROR',
        Throttled: 'RATE_LIMITED',
    }

    return error_codes.get(type(exc), 'ERROR')


def _get_error_message(exc, response):
    """Extract human-readable message."""
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, str):
            return exc.detail
        if isinstance(exc.detail, list):
            return exc.detail[0] if exc.detail else 'An error occurred'
    return 'An error occurred'


def _get_error_details(exc, response):
    """Extract field-level error details."""
    if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
        return exc.detail
    return None


# Custom Exceptions
class ConflictError(Exception):
    """409 Conflict - Resource state conflict."""

    status_code = status.HTTP_409_CONFLICT
    default_code = 'CONFLICT'

    def __init__(self, message='Resource conflict'):
        self.detail = message


class BusinessRuleError(Exception):
    """422 Unprocessable Entity - Business rule violation."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = 'BUSINESS_RULE_VIOLATION'

    def __init__(self, message, code=None):
        self.detail = message
        self.code = code or self.default_code
