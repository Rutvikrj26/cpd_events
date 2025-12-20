"""
Validators for JSON fields and other custom validation.
"""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


def validate_field_positions_schema(value):
    """
    Validate certificate template field positions JSON.

    Expected schema:
    {
        "field_name": {
            "x": <int>,
            "y": <int>,
            "font_size": <int>,
            "font": <str>,
            "align": "left" | "center" | "right",
            "color": <str, optional>,
            "image_url": <str, optional>,
            "width": <int, optional>
        },
        ...
    }
    """
    if not isinstance(value, dict):
        raise ValidationError("Field positions must be a dictionary")

    valid_fields = {
        'attendee_name',
        'event_title',
        'event_date',
        'cpd_credits',
        'cpd_type',
        'certificate_id',
        'organizer_name',
        'signature',
        'issue_date',
        'qr_code',
    }
    valid_alignments = {'left', 'center', 'right'}

    for field_name, config in value.items():
        if field_name not in valid_fields:
            raise ValidationError(f"Unknown field: {field_name}")

        if not isinstance(config, dict):
            raise ValidationError(f"Config for {field_name} must be a dictionary")

        # Required position fields
        if 'x' not in config or 'y' not in config:
            raise ValidationError(f"Field {field_name} must have x and y coordinates")

        if not isinstance(config['x'], (int, float)):
            raise ValidationError(f"Field {field_name}: x must be a number")

        if not isinstance(config['y'], (int, float)):
            raise ValidationError(f"Field {field_name}: y must be a number")

        # Optional fields validation
        if 'align' in config and config['align'] not in valid_alignments:
            raise ValidationError(f"Field {field_name}: align must be left, center, or right")

        if 'font_size' in config and not isinstance(config['font_size'], int):
            raise ValidationError(f"Field {field_name}: font_size must be an integer")


def validate_zoom_settings_schema(value):
    """
    Validate Zoom meeting settings JSON.

    Expected schema:
    {
        "waiting_room": <bool>,
        "join_before_host": <bool>,
        "mute_upon_entry": <bool>,
        "auto_recording": "none" | "local" | "cloud"
    }
    """
    if not isinstance(value, dict):
        raise ValidationError("Zoom settings must be a dictionary")

    valid_keys = {'waiting_room', 'join_before_host', 'mute_upon_entry', 'auto_recording', 'enabled'}
    valid_recording = {'none', 'local', 'cloud'}

    for key, val in value.items():
        if key not in valid_keys:
            raise ValidationError(f"Unknown Zoom setting: {key}")

        if key in {'waiting_room', 'join_before_host', 'mute_upon_entry', 'enabled'} and not isinstance(val, bool):
            raise ValidationError(f"Zoom setting {key} must be boolean")

        if key == 'auto_recording' and val not in valid_recording:
            raise ValidationError(f"auto_recording must be one of: {valid_recording}")


def validate_certificate_data_schema(value):
    """
    Validate certificate snapshot data JSON.

    Expected schema:
    {
        "attendee_name": <str, required>,
        "event_title": <str, required>,
        "event_date": <str, required, ISO date>,
        "cpd_type": <str, optional>,
        "cpd_credits": <str, optional>,
        "organizer_name": <str, required>,
        "issued_date": <str, required, ISO date>
    }
    """
    if not isinstance(value, dict):
        raise ValidationError("Certificate data must be a dictionary")

    required = {'attendee_name', 'event_title', 'event_date', 'organizer_name', 'issued_date'}

    for field in required:
        if field not in value:
            raise ValidationError(f"Missing required field: {field}")
        if not isinstance(value[field], str):
            raise ValidationError(f"Field {field} must be a string")


# Color hex code validator
hex_color_validator = RegexValidator(regex=r'^#[0-9A-Fa-f]{6}$', message='Enter a valid hex color (e.g., #FF5733)')


def validate_timezone(value):
    """Validate that value is a valid timezone string."""
    import pytz

    if value not in pytz.all_timezones:
        raise ValidationError(f"'{value}' is not a valid timezone")


# Slug with UUID prefix validator
slug_validator = RegexValidator(
    regex=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', message='Enter a valid slug (lowercase letters, numbers, hyphens only)'
)
