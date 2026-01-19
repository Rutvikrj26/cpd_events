import logging
from typing import Any

from django.db import transaction
from django.utils.text import slugify
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.utils import generate_unique_slug
from events.models import Event, EventCustomField

logger = logging.getLogger(__name__)


class EventService:
    """
    Service for managing Events.
    Handles creation, updates, and subscription limit enforcement.
    """

    @staticmethod
    def create_event(user, data: dict[str, Any]) -> Event:
        """
        Create a new event, enforcing subscription limits.

        Args:
            user: The user creating the event.
            data: Validated data for the event (from serializer).

        Returns:
            The created Event instance.

        Raises:
            PermissionDenied: If subscription limits are reached.
        """
        # 1. Prepare Data
        # Pop custom fields to handle separately
        custom_fields_data = data.pop("custom_fields", [])
        speakers_data = data.pop("speakers", None)

        # Generate unique slug if not present
        if "slug" not in data:
            title = data["title"]
            base_slug = slugify(title)[:40]
            data["slug"] = generate_unique_slug(Event, base_slug)

        # 2. Create Event & Increment Counters (Atomic)
        with transaction.atomic():
            # Check limits and increment atomically
            # This handles plan capability, status checks, and limit enforcement
            from billing.capability_service import capability_service

            result = capability_service.check_and_increment_event(user)
            if not result.allowed:
                raise PermissionDenied(result.error_message)

            # Create the event
            event = Event.objects.create(owner=user, **data)

            # Create custom fields
            for position, field_data in enumerate(custom_fields_data):
                field_data["position"] = position
                EventCustomField.objects.create(event=event, **field_data)

            # Set speakers
            if speakers_data:
                event.speakers.set(speakers_data)

        logger.info(f"Event created: {event.uuid} by user {user.id}")
        return event


# Singleton instance
event_service = EventService()
