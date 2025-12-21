"""
Event services for Zoom meeting management and event operations.
"""

import logging
from typing import Any, Optional

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


class ZoomMeetingService:
    """
    Service for managing Zoom meetings for events.
    """

    API_URL = 'https://api.zoom.us/v2'

    def _get_access_token(self, user) -> str | None:
        """Get valid access token for user."""
        from accounts.models import ZoomConnection
        from accounts.services import zoom_service

        try:
            connection = ZoomConnection.objects.get(user=user, is_active=True)
            return zoom_service.get_access_token(connection)
        except ZoomConnection.DoesNotExist:
            return None

    def create_meeting(self, event) -> dict[str, Any]:
        """
        Create Zoom meeting for an event.

        Args:
            event: Event to create meeting for

        Returns:
            Dict with success status and meeting details
        """
        access_token = self._get_access_token(event.owner)
        if not access_token:
            return {'success': False, 'error': 'Zoom not connected'}

        try:
            # Prepare meeting settings
            meeting_settings = event.zoom_settings or {}

            meeting_data = {
                'topic': event.title,
                'type': 2,  # Scheduled meeting
                'start_time': event.starts_at.strftime('%Y-%m-%dT%H:%M:%S'),
                'duration': event.duration_minutes,
                'timezone': event.timezone,
                'agenda': event.short_description or '',
                'settings': {
                    'waiting_room': meeting_settings.get('waiting_room', True),
                    'join_before_host': meeting_settings.get('join_before_host', False),
                    'mute_upon_entry': meeting_settings.get('mute_upon_entry', True),
                    'auto_recording': meeting_settings.get('auto_recording', 'cloud'),
                    'approval_type': 2,  # No registration required
                    'registration_type': 1,  # Attendees register once
                },
            }

            response = requests.post(
                f"{self.API_URL}/users/me/meetings",
                headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
                json=meeting_data,
                timeout=30,
            )

            if response.status_code not in [200, 201]:
                logger.error(f"Zoom meeting creation failed: {response.text}")
                return {'success': False, 'error': response.text}

            zoom_data = response.json()

            # Update event with Zoom details
            event.zoom_meeting_id = str(zoom_data.get('id', ''))
            event.zoom_join_url = zoom_data.get('join_url', '')
            event.zoom_start_url = zoom_data.get('start_url', '')
            event.zoom_password = zoom_data.get('password', '')
            event.save(update_fields=['zoom_meeting_id', 'zoom_join_url', 'zoom_start_url', 'zoom_password', 'updated_at'])

            return {'success': True, 'meeting_id': event.zoom_meeting_id, 'join_url': event.zoom_join_url}

        except Exception as e:
            logger.error(f"Zoom meeting creation failed: {e}")
            return {'success': False, 'error': str(e)}

    def update_meeting(self, event) -> dict[str, Any]:
        """
        Update Zoom meeting for an event.

        Args:
            event: Event to update meeting for

        Returns:
            Dict with success status
        """
        if not event.zoom_meeting_id:
            return self.create_meeting(event)

        access_token = self._get_access_token(event.owner)
        if not access_token:
            return {'success': False, 'error': 'Zoom not connected'}

        try:
            meeting_settings = event.zoom_settings or {}

            meeting_data = {
                'topic': event.title,
                'start_time': event.starts_at.strftime('%Y-%m-%dT%H:%M:%S'),
                'duration': event.duration_minutes,
                'timezone': event.timezone,
                'agenda': event.short_description or '',
                'settings': {
                    'waiting_room': meeting_settings.get('waiting_room', True),
                    'join_before_host': meeting_settings.get('join_before_host', False),
                    'mute_upon_entry': meeting_settings.get('mute_upon_entry', True),
                },
            }

            response = requests.patch(
                f"{self.API_URL}/meetings/{event.zoom_meeting_id}",
                headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
                json=meeting_data,
                timeout=30,
            )

            if response.status_code not in [200, 204]:
                logger.error(f"Zoom meeting update failed: {response.text}")
                return {'success': False, 'error': response.text}

            return {'success': True}

        except Exception as e:
            logger.error(f"Zoom meeting update failed: {e}")
            return {'success': False, 'error': str(e)}

    def delete_meeting(self, event) -> bool:
        """
        Delete Zoom meeting for an event.

        Args:
            event: Event to delete meeting for

        Returns:
            True if successful
        """
        if not event.zoom_meeting_id:
            return True

        access_token = self._get_access_token(event.owner)
        if not access_token:
            return False

        try:
            response = requests.delete(
                f"{self.API_URL}/meetings/{event.zoom_meeting_id}",
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=30,
            )

            if response.status_code in [200, 204, 404]:  # 404 = already deleted
                event.zoom_meeting_id = ''
                event.zoom_join_url = ''
                event.zoom_start_url = ''
                event.zoom_password = ''
                event.save(update_fields=['zoom_meeting_id', 'zoom_join_url', 'zoom_start_url', 'zoom_password', 'updated_at'])
                return True

            return False

        except Exception as e:
            logger.error(f"Zoom meeting deletion failed: {e}")
            return False


class EventService:
    """
    Service for event operations.
    """

    def duplicate_event(
        self, event, new_title: str | None = None, new_start: Optional['timezone.datetime'] = None
    ) -> dict[str, Any]:
        """
        Create a complete copy of an event.

        Args:
            event: Event to duplicate
            new_title: Optional new title
            new_start: Optional new start time

        Returns:
            Dict with success status and new event
        """
        try:
            # Use model's duplicate method
            new_event = event.duplicate(new_title=new_title, new_start=new_start)

            # Save the new event
            new_event.save()

            # Duplicate custom fields
            for field in event.custom_fields.all():
                field.pk = None
                field.uuid = None
                field.event = new_event
                field.save()

            return {'success': True, 'event': new_event}

        except Exception as e:
            logger.error(f"Event duplication failed: {e}")
            return {'success': False, 'error': str(e)}

    def cancel_event(self, event, reason: str = '', cancelled_by=None, notify_registrants: bool = True) -> dict[str, Any]:
        """
        Cancel an event and handle notifications.

        Args:
            event: Event to cancel
            reason: Cancellation reason
            cancelled_by: User who cancelled
            notify_registrants: Whether to notify registered users

        Returns:
            Dict with success status
        """
        try:
            # Cancel the event
            event.cancel(user=cancelled_by, reason=reason)

            # Delete Zoom meeting if exists
            if event.zoom_meeting_id:
                zoom_meeting_service.delete_meeting(event)

            # Notify registrants
            if notify_registrants:
                self._notify_cancellation(event, reason)

            return {'success': True}

        except Exception as e:
            logger.error(f"Event cancellation failed: {e}")
            return {'success': False, 'error': str(e)}

    def _notify_cancellation(self, event, reason: str):
        """Send cancellation notifications to registrants."""
        # TODO: Implement email notifications
        from registrations.models import Registration

        registrations = Registration.objects.filter(event=event, status__in=['confirmed', 'waitlisted'])

        # Queue notification tasks
        for reg in registrations:
            # TODO: Send email via task queue
            logger.info(f"Would notify {reg.user.email} of cancellation")


# Singleton instances
zoom_meeting_service = ZoomMeetingService()
event_service = EventService()
