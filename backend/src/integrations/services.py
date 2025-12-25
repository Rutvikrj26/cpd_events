"""
Integration services for email, webhooks, and external providers.
"""

import logging
from typing import Any

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails.

    Supports multiple backends and template rendering.
    """

    # Email template mapping
    TEMPLATES = {
        'registration_confirmation': 'emails/registration_confirmation.html',
        'event_reminder': 'emails/event_reminder.html',
        'certificate_issued': 'emails/certificate_issued.html',
        'event_cancelled': 'emails/event_cancelled.html',
        'password_reset': 'emails/password_reset.html',
        'email_verification': 'emails/email_verification.html',
        'invitation': 'emails/invitation.html',
    }

    # Subject lines
    SUBJECTS = {
        'registration_confirmation': 'Registration Confirmed: {event_title}',
        'event_reminder': 'Reminder: {event_title} starts soon',
        'certificate_issued': 'Your Certificate: {event_title}',
        'event_cancelled': 'Event Cancelled: {event_title}',
        'password_reset': 'Password Reset Request',
        'email_verification': 'Verify Your Email',
        'invitation': "You're invited: {event_title}",
    }

    def send_email(self, template: str, recipient: str, context: dict[str, Any], subject: str | None = None) -> bool:
        """
        Send a templated email.

        Args:
            template: Template name
            recipient: Recipient email
            context: Template context
            subject: Optional custom subject

        Returns:
            True if successful
        """
        from integrations.models import EmailLog

        try:
            # Render subject
            if subject is None:
                subject_template = self.SUBJECTS.get(template, 'Notification')
                subject = subject_template.format(**context)

            # Render body
            template_path = self.TEMPLATES.get(template)
            if template_path:
                try:
                    html_body = render_to_string(template_path, context)
                except Exception:
                    html_body = self._build_simple_html(template, context)
            else:
                html_body = self._build_simple_html(template, context)

            # Send via configured backend
            success = self._send(recipient, subject, html_body)

            # Log email
            EmailLog.objects.create(
                recipient_email=recipient,
                email_type=template,
                subject=subject,
                delivery_status='sent' if success else 'failed',
                sent_at=timezone.now() if success else None,
            )

            return success

        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    def send_bulk_emails(
        self, template: str, recipients: list[dict[str, Any]], common_context: dict | None = None
    ) -> dict[str, Any]:
        """
        Send emails to multiple recipients.

        Args:
            template: Template name
            recipients: List of {email, context} dicts
            common_context: Context shared by all emails

        Returns:
            Dict with success/failure counts
        """
        results = {'total': len(recipients), 'sent': 0, 'failed': 0}

        for recipient in recipients:
            email = recipient.get('email')
            ctx = {**(common_context or {}), **(recipient.get('context', {}))}

            if self.send_email(template, email, ctx):
                results['sent'] += 1
            else:
                results['failed'] += 1

        return results

    def _send(self, recipient: str, subject: str, html_body: str) -> bool:
        """Send email using Django's email backend."""
        try:
            from django.core.mail import send_mail

            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')

            send_mail(
                subject=subject,
                message='',  # Plain text fallback
                from_email=from_email,
                recipient_list=[recipient],
                html_message=html_body,
                fail_silently=False,
            )

            return True

        except Exception as e:
            logger.error(f"Email send via backend failed: {e}")
            return False

    def _build_simple_html(self, template: str, context: dict) -> str:
        """Build simple HTML email when template not found."""
        lines = [
            f"<p>Hello {context.get('user_name', 'there')},</p>",
        ]

        if template == 'certificate_issued':
            lines.append(f"<p>Your certificate for <strong>{context.get('event_title', 'the event')}</strong> is ready.</p>")
            if context.get('certificate_url'):
                lines.append(f"<p><a href='{context['certificate_url']}'>Download Certificate</a></p>")

        elif template == 'registration_confirmation':
            lines.append(f"<p>You are registered for <strong>{context.get('event_title', 'the event')}</strong>.</p>")

        elif template == 'event_reminder':
            lines.append(f"<p><strong>{context.get('event_title', 'Your event')}</strong> starts soon.</p>")

        else:
            for key, value in context.items():
                if isinstance(value, str) and key not in ['user_name']:
                    lines.append(f"<p>{key}: {value}</p>")

        lines.append("<p>Best regards,<br>The Team</p>")

        return '\n'.join(lines)


class WebhookProcessor:
    """
    Service for processing incoming webhooks.
    """

    def process_zoom_webhook(self, log) -> bool:
        """
        Process a Zoom webhook log entry.

        Args:
            log: ZoomWebhookLog instance

        Returns:
            True if processed successfully
        """
        try:
            event_type = log.event_type
            event_type = log.event_type
            # log.payload is the full request data
            # The actual event data is inside the 'payload' key
            # { "event": "...", "payload": { "object": { ... } } }
            payload = log.payload.get('payload', {})

            handler = self._get_zoom_handler(event_type)
            if handler:
                return handler(payload)

            logger.info(f"Unhandled Zoom webhook: {event_type}")
            return True

        except Exception as e:
            logger.error(f"Zoom webhook processing failed: {e}")
            log.error_message = str(e)
            log.save(update_fields=['error_message', 'updated_at'])
            return False

    def _get_zoom_handler(self, event_type: str):
        """Get handler for Zoom event type."""
        handlers = {
            'meeting.participant_joined': self._handle_participant_joined,
            'meeting.participant_left': self._handle_participant_left,
            'meeting.ended': self._handle_meeting_ended,
            'recording.completed': self._handle_recording_completed,
        }
        return handlers.get(event_type)

    def _handle_participant_joined(self, payload: dict) -> bool:
        """Handle participant join event."""
        from events.models import Event
        from registrations.models import AttendanceRecord, Registration
        from django.utils.dateparse import parse_datetime

        # Extract data
        meeting_id = str(payload.get('object', {}).get('id', ''))
        participant = payload.get('object', {}).get('participant', {})
        
        zoom_user_id = participant.get('user_id', '')
        user_name = participant.get('user_name', '')
        user_email = participant.get('email', '')
        participant_uuid = participant.get('id', '') # Unique for this session
        join_time_str = participant.get('join_time')
        
        join_time = parse_datetime(join_time_str) if join_time_str else None

        logger.info(f"Participant joined meeting {meeting_id}: {user_email}")

        if not meeting_id or not join_time:
            logger.warning("Missing meeting_id or join_time in payload")
            return False

        # Find Event
        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
        except Event.DoesNotExist:
            logger.warning(f"Event not found for Zoom meeting ID: {meeting_id}")
            return True # Return True to acknowledge webhook receipt

        # Find Registration (if any)
        registration = None
        if user_email:
            registration = Registration.objects.filter(
                event=event, 
                email__iexact=user_email,
                deleted_at__isnull=True
            ).first()

        # Create Attendance Record
        # We use get_or_create to handle potential duplicate webhooks
        AttendanceRecord.objects.get_or_create(
            event=event,
            zoom_participant_id=participant_uuid,
            join_time=join_time,
            defaults={
                'registration': registration,
                'zoom_user_id': zoom_user_id,
                'zoom_user_email': user_email,
                'zoom_user_name': user_name,
                'is_matched': registration is not None,
                'matched_at': timezone.now() if registration else None
            }
        )

        # Update registration summary immediately if matched
        if registration:
            registration.update_attendance_summary()
            
        return True

    def _handle_participant_left(self, payload: dict) -> bool:
        """Handle participant leave event."""
        from events.models import Event
        from registrations.models import AttendanceRecord
        from django.utils.dateparse import parse_datetime

        meeting_id = str(payload.get('object', {}).get('id', ''))
        participant = payload.get('object', {}).get('participant', {})
        
        participant_uuid = participant.get('id', '')
        leave_time_str = participant.get('leave_time')
        
        leave_time = parse_datetime(leave_time_str) if leave_time_str else None

        logger.info(f"Participant left meeting {meeting_id}")
        
        if not meeting_id or not participant_uuid or not leave_time:
             return False

        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
        except Event.DoesNotExist:
            return True

        # Find the specific open record
        record = AttendanceRecord.objects.filter(
            event=event,
            zoom_participant_id=participant_uuid,
            leave_time__isnull=True
        ).order_by('-join_time').first()

        if record:
            record.participant_left(leave_time=leave_time)
            logger.info(f"Closed attendance record for {record}")
        else:
            logger.warning(f"No open attendance record found for participant {participant_uuid} in meeting {meeting_id}")

        return True

    def _handle_meeting_ended(self, payload: dict) -> bool:
        """Handle meeting end event."""
        from events.models import Event

        meeting_id = str(payload.get('object', {}).get('id', ''))

        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
            # Auto-complete if still live
            if event.status == 'live':
                event.complete()
            return True
        except Event.DoesNotExist:
            return True

    def _handle_recording_completed(self, payload: dict) -> bool:
        """Handle recording completed event."""
        from integrations.models import ZoomRecording

        recording_data = payload.get('object', {})
        meeting_id = str(recording_data.get('id', ''))

        # Find associated event
        from events.models import Event

        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
        except Event.DoesNotExist:
            return True

        # Create recording record
        ZoomRecording.objects.create(
            event=event,
            zoom_meeting_id=meeting_id,
            recording_id=recording_data.get('uuid', ''),
            topic=recording_data.get('topic', ''),
            recording_type=recording_data.get('recording_type', 'cloud'),
            status='completed',
            total_size_bytes=recording_data.get('total_size', 0),
            share_url=recording_data.get('share_url', ''),
            password=recording_data.get('password', ''),
        )

        return True


class AttendanceMatcher:
    """
    Service for matching Zoom attendance to registrations.
    """

    def match_attendance(self, event) -> dict[str, Any]:
        """
        Match Zoom participant data to event registrations.

        Args:
            event: Event to match attendance for

        Returns:
            Dict with match results
        """
        from registrations.models import AttendanceRecord, Registration

        results = {'matched': 0, 'unmatched': 0, 'eligible': 0, 'ineligible': 0}

        # Get all registrations for event
        registrations = Registration.objects.filter(event=event, status='confirmed').select_related('user')

        # Get attendance records
        attendance_records = AttendanceRecord.objects.filter(registration__event=event)

        for reg in registrations:
            # Calculate total attendance
            records = attendance_records.filter(registration=reg)

            total_minutes = sum(r.duration_minutes for r in records)

            # Check eligibility based on event settings
            required_minutes = event.duration_minutes * (event.minimum_attendance_percent / 100)
            is_eligible = total_minutes >= required_minutes

            # Update registration
            reg.attendance_eligible = is_eligible
            if records.exists():
                reg.status = 'attended'
                results['matched'] += 1
            else:
                results['unmatched'] += 1

            if is_eligible:
                results['eligible'] += 1
            else:
                results['ineligible'] += 1

            reg.save(update_fields=['attendance_eligible', 'status', 'updated_at'])

        return results


# Singleton instances
email_service = EmailService()
webhook_processor = WebhookProcessor()
attendance_matcher = AttendanceMatcher()
