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
        # Check Individual Subscription Limits — best-effort in institutional
        # deployments where the subscription model may not expose legacy
        # SaaS-era attributes.
        subscription = getattr(user, 'subscription', None)

        if subscription and hasattr(subscription, 'can_create_events'):
            if not subscription.can_create_events:
                if getattr(subscription, 'is_access_blocked', False):
                    raise PermissionDenied("Your subscription has expired. Please upgrade to continue creating events.")
                elif getattr(subscription, 'is_trial_expired', False):
                    raise PermissionDenied("Your trial has ended. Please upgrade to a paid plan to create new events.")
                elif hasattr(subscription, 'check_event_limit') and not subscription.check_event_limit():
                    raise PermissionDenied("You have reached your monthly event limit. Please upgrade for more events.")

        # Pop custom fields to handle separately
        custom_fields_data = data.pop('custom_fields', [])
        speakers_data = data.pop('speakers', None)

        # Generate unique slug if not present
        if 'slug' not in data:
            title = data.get('title', '')
            base_slug = slugify(title)[:40]
            data['slug'] = generate_unique_slug(Event, base_slug)

        # Create Event & Increment Counters (Atomic)
        with transaction.atomic():
            event = Event.objects.create(owner=user, **data)

            for position, field_data in enumerate(custom_fields_data):
                field_data['position'] = position
                EventCustomField.objects.create(event=event, **field_data)

            if speakers_data:
                event.speakers.set(speakers_data)

            sub = getattr(user, 'subscription', None)
            if sub and hasattr(sub, 'increment_events'):
                sub.increment_events()

        logger.info("Event created: %s", event.uuid)
        return event


# Singleton instance
event_service = EventService()
