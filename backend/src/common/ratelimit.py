"""
Rate limiting utilities using django-ratelimit.

This module provides decorators and utilities for rate limiting specific endpoints
that need additional protection beyond DRF's built-in throttling.
"""

from functools import wraps
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit


def webhook_ratelimit(group=None, key="ip", rate="100/m", method="POST"):
    """
    Rate limit decorator for webhook endpoints.

    Args:
        group: Group name for the rate limit (optional)
        key: What to use as the key for rate limiting (default: 'ip')
        rate: Rate limit string (default: '100/m' = 100 requests per minute)
        method: HTTP method to rate limit (default: 'POST')

    Returns:
        Decorator function

    Example:
        @webhook_ratelimit(group='stripe_webhooks', rate='200/m')
        def post(self, request):
            # Handle webhook
            pass
    """

    def decorator(view_func):
        @wraps(view_func)
        @ratelimit(group=group, key=key, rate=rate, method=method)
        def wrapped_view(request, *args, **kwargs):
            # Check if rate limit was exceeded
            if getattr(request, "limited", False):
                return JsonResponse(
                    {
                        "error": "Rate limit exceeded",
                        "code": "RATE_LIMIT_EXCEEDED",
                        "detail": f"Too many requests. Please try again later.",
                    },
                    status=429,
                )
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def auth_ratelimit(group=None, key="ip", rate="5/m", method=["GET", "POST"]):
    """
    Rate limit decorator for authentication endpoints.

    More restrictive than webhook rate limiting to prevent brute force attacks.

    Args:
        group: Group name for the rate limit (optional)
        key: What to use as the key for rate limiting (default: 'ip')
        rate: Rate limit string (default: '5/m' = 5 requests per minute)
        method: HTTP methods to rate limit (default: GET and POST)

    Returns:
        Decorator function

    Example:
        @auth_ratelimit(group='password_reset', rate='3/h')
        def post(self, request):
            # Handle password reset
            pass
    """

    def decorator(view_func):
        @wraps(view_func)
        @ratelimit(group=group, key=key, rate=rate, method=method)
        def wrapped_view(request, *args, **kwargs):
            # Check if rate limit was exceeded
            if getattr(request, "limited", False):
                return JsonResponse(
                    {
                        "error": "Too many authentication attempts",
                        "code": "AUTH_RATE_LIMIT_EXCEEDED",
                        "detail": f"Too many requests. Please try again later.",
                    },
                    status=429,
                )
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def api_ratelimit(group=None, key="user_or_ip", rate="1000/h", method=["GET", "POST", "PUT", "PATCH", "DELETE"]):
    """
    Rate limit decorator for general API endpoints.

    Uses user_or_ip as the key, which means:
    - Authenticated users are rate limited per user
    - Anonymous users are rate limited per IP

    Args:
        group: Group name for the rate limit (optional)
        key: What to use as the key for rate limiting (default: 'user_or_ip')
        rate: Rate limit string (default: '1000/h' = 1000 requests per hour)
        method: HTTP methods to rate limit (default: all major methods)

    Returns:
        Decorator function

    Example:
        @api_ratelimit(group='events_api', rate='500/h')
        def get(self, request):
            # Handle API request
            pass
    """

    def decorator(view_func):
        @wraps(view_func)
        @ratelimit(group=group, key=key, rate=rate, method=method)
        def wrapped_view(request, *args, **kwargs):
            # Check if rate limit was exceeded
            if getattr(request, "limited", False):
                return JsonResponse(
                    {
                        "error": "API rate limit exceeded",
                        "code": "API_RATE_LIMIT_EXCEEDED",
                        "detail": f"Too many requests. Please try again later.",
                    },
                    status=429,
                )
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator
