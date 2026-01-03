
import logging
from typing import Any, Dict

from django.db import transaction
from django.utils.text import slugify
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.utils import generate_unique_slug
from events.models import Event, EventCustomField
from organizations.models import Organization

logger = logging.getLogger(__name__)


class EventService:
    """
    Service for managing Events.
    Handles creation, updates, and subscription limit enforcement.
    """

    @staticmethod
    def create_event(user, data: Dict[str, Any], organization_uuid: str = None) -> Event:
        """
        Create a new event, enforcing subscription limits.

        Args:
            user: The user creating the event.
            data: Validated data for the event (from serializer).
            organization_uuid: Optional UUID of the organization.

        Returns:
            The created Event instance.

        Raises:
            ValidationError: If organization not found.
            PermissionDenied: If subscription limits are reached.
        """
        organization = None

        # 1. Determine Context (Organization vs Personal)
        if organization_uuid:
            try:
                organization = Organization.objects.get(uuid=organization_uuid)
            except Organization.DoesNotExist:
                raise ValidationError("Organization not found")

            # Validate User Permission for Organization (Assuming ViewSet checks this, but good to double check if needed)
            # For now, we assume the caller (ViewSet) has verified the user can manage this org.

            # 2. Check Organization Subscription Limits
            if hasattr(organization, 'subscription'):
                org_subscription = organization.subscription
                if not org_subscription.check_event_limit():
                    limit = org_subscription.config.get('events_per_month', 0)
                    raise PermissionDenied(
                        f"Organization has reached its event limit of {limit} events this month. "
                        f"Please upgrade your plan to create more events."
                    )
        else:
            # 3. Check Individual Subscription Limits
            subscription = getattr(user, 'subscription', None)

            if subscription:
                if not subscription.can_create_events:
                    if subscription.is_access_blocked:
                        raise PermissionDenied(
                            "Your subscription has expired. Please upgrade to continue creating events."
                        )
                    elif subscription.is_trial_expired:
                        raise PermissionDenied(
                            "Your trial has ended. Please upgrade to a paid plan to create new events."
                        )
                    elif not subscription.check_event_limit():
                        raise PermissionDenied(
                            "You have reached your monthly event limit. Please upgrade for more events."
                        )

        # 4. Prepare Data
        # Pop custom fields to handle separately
        custom_fields_data = data.pop('custom_fields', [])
        speakers_data = data.pop('speakers', None)

        # Generate unique slug (M1) if not present
        if 'slug' not in data:
            title = data.get('title', '')
            base_slug = slugify(title)[:40]
            data['slug'] = generate_unique_slug(Event, base_slug)

        # 5. Create Event & Increment Counters (Atomic)
        with transaction.atomic():
            # Create the event
            event = Event.objects.create(
                owner=user,
                organization=organization,
                **data
            )

            # Create custom fields
            for position, field_data in enumerate(custom_fields_data):
                field_data['position'] = position
                EventCustomField.objects.create(event=event, **field_data)
            
            # Set speakers
            if speakers_data:
                event.speakers.set(speakers_data)

            # Increment Counters
            if organization and hasattr(organization, 'subscription'):
                organization.subscription.increment_events()
            elif not organization and hasattr(user, 'subscription'):
                user.subscription.increment_events()

        logger.info(f"Event created: {event.uuid} (Org: {organization_uuid})")
        return event


# Singleton instance
event_service = EventService()
