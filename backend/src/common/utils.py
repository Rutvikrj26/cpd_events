"""
Utility functions for the CPD Events platform.
"""

import secrets
import string

from rest_framework import status
from rest_framework.response import Response
from django.utils.text import slugify


def error_response(message, code='ERROR', details=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Return a consistent error response.
    
    Format:
    {
        "error": {
            "code": "CODE",
            "message": "Message",
            "details": {...}
        }
    }
    """
    return Response(
        {
            'error': {
                'code': code,
                'message': message,
                'details': details,
            }
        },
        status=status_code,
    )


def generate_unique_slug(model_or_slugs, base_string, max_length=200):
    """
    Generate a unique slug from a string.

    Args:
        model_or_slugs: Either a Django model class (checks DB) or a set of existing slugs
        base_string: String to slugify
        max_length: Maximum slug length

    Returns:
        Unique slug string
    """
    from django.db.models import Model

    base_slug = slugify(base_string)[: max_length - 9]  # Leave room for suffix

    # Determine how to check for existing slugs
    if model_or_slugs is None:
        return base_slug

    if isinstance(model_or_slugs, type) and issubclass(model_or_slugs, Model):
        # It's a model class - query the database
        def slug_exists(slug):
            # Use all_objects if available to check against soft-deleted records too
            manager = getattr(model_or_slugs, 'all_objects', model_or_slugs.objects)
            return manager.filter(slug=slug).exists()

    elif isinstance(model_or_slugs, set):
        # It's a set of existing slugs
        def slug_exists(slug):
            return slug in model_or_slugs

    else:
        return base_slug

    if not slug_exists(base_slug):
        return base_slug

    # Add random suffix
    for _ in range(100):
        suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        candidate = f"{base_slug}-{suffix}"
        if not slug_exists(candidate):
            return candidate

    raise ValueError("Could not generate unique slug")


def generate_verification_code(length=22):
    """
    Generate a URL-safe verification code.

    Default length of 22 chars provides ~131 bits of entropy.
    """
    return secrets.token_urlsafe(length)[:length]


def generate_short_code(length=8):
    """
    Generate a short alphanumeric code.

    Useful for display (e.g., certificate ID shown on document).
    Excludes ambiguous characters (0, O, l, 1, I).
    """
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def normalize_email(email):
    """
    Normalize an email address.

    - Lowercase
    - Strip whitespace
    """
    if email is None:
        return None
    return email.lower().strip()


def mask_email(email):
    """
    Mask an email for display.

    Example: john.doe@example.com → j***e@example.com
    """
    if not email or '@' not in email:
        return email

    local, domain = email.rsplit('@', 1)
    masked_local = local[0] + '***' if len(local) <= 2 else local[0] + '***' + local[-1]

    return f"{masked_local}@{domain}"


def format_duration(minutes):
    """
    Format duration in minutes to human-readable string.

    Examples:
        30 → "30 minutes"
        60 → "1 hour"
        90 → "1 hour 30 minutes"
    """
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"

    return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
