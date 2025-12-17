"""
Custom model fields for the CPD Events platform.
"""

import base64

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class LowercaseEmailField(models.EmailField):
    """
    Email field that automatically converts to lowercase.

    Ensures consistent email matching across the application.
    Always use this instead of models.EmailField.
    """

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is not None:
            value = value.lower().strip()
        return value

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        if value is not None:
            value = value.lower().strip()
            setattr(model_instance, self.attname, value)
        return value


class EncryptedTextField(models.TextField):
    """
    Text field with Fernet encryption for sensitive data.

    Use for:
    - OAuth access tokens
    - OAuth refresh tokens
    - API keys
    - Other sensitive credentials

    Note: Encrypted fields cannot be queried with filters.
    Requires ENCRYPTION_KEY in settings.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_fernet(self):
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            raise ValueError("ENCRYPTION_KEY must be set in settings")
        # Ensure key is proper Fernet key (32 url-safe base64 bytes)
        if len(key) == 44:  # Already a proper Fernet key
            return Fernet(key.encode())
        # Otherwise, derive a key from the provided value
        key_bytes = key.encode()[:32].ljust(32, b'\0')
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(fernet_key)

    def get_prep_value(self, value):
        if value is None:
            return None
        f = self._get_fernet()
        return f.encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        f = self._get_fernet()
        try:
            return f.decrypt(value.encode()).decode()
        except Exception:
            # Return as-is if decryption fails (might be already decrypted)
            return value
