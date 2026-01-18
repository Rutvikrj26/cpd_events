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
        'badge_issued': 'emails/badge_issued.html',
        'event_cancelled': 'emails/event_cancelled.html',
        'password_reset': 'emails/password_reset.html',
        'email_verification': 'emails/email_verification.html',
        'invitation': 'emails/invitation.html',
        'organization_invitation': 'emails/organization_invitation.html',
        'payment_failed': 'emails/payment_failed.html',
        'waitlist_promotion': 'emails/waitlist_promotion.html',
        'refund_processed': 'emails/refund_processed.html',
        'payment_method_expired': 'emails/payment_method_expired.html',
        'trial_ending': 'emails/trial_ending.html',
    }

    # Subject lines
    SUBJECTS = {
        'registration_confirmation': 'Registration Confirmed: {event_title}',
        'event_reminder': 'Reminder: {event_title} starts soon',
        'certificate_issued': 'Your Certificate: {event_title}',
        'badge_issued': 'You earned a badge: {badge_name}',
        'event_cancelled': 'Event Cancelled: {event_title}',
        'password_reset': 'Password Reset Request',
        'email_verification': 'Verify Your Email',
        'invitation': "You're invited: {event_title}",
        'organization_invitation': "You're invited to join {organization_name}",
        'payment_failed': "Payment Failed: Invoice #{invoice_number}",
        'waitlist_promotion': "Spot Available: {event_title}",
        'refund_processed': "Refund Processed: {event_title}",
        'payment_method_expired': "Payment Method Expired",
        'trial_ending': "Your Trial Is Ending Soon",
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
                status='sent' if success else 'failed',
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

        elif template == 'badge_issued':
            lines.append(f"<p>Congratulations! You have earned the <strong>{context.get('badge_name', 'Badge')}</strong> for <strong>{context.get('event_title', 'the event')}</strong>.</p>")
            if context.get('badge_url'):
                lines.append(f"<p><img src='{context['badge_url']}' alt='Badge' width='200' /></p>")
                lines.append(f"<p><a href='{context.get('verification_url', '#')}'>View & Verify Badge</a></p>")

        elif template == 'registration_confirmation':
            lines.append(f"<p>You are registered for <strong>{context.get('event_title', 'the event')}</strong>.</p>")

        elif template == 'event_reminder':
            lines.append(f"<p><strong>{context.get('event_title', 'Your event')}</strong> starts soon.</p>")

        elif template == 'organization_invitation':
            lines.append(
                f"<p>{context.get('inviter_name', 'Someone')} has invited you to join <strong>{context.get('organization_name', 'their organization')}</strong> as a <strong>{context.get('role', 'member')}</strong>.</p>"
            )
            if context.get('invitation_url'):
                lines.append(
                    f"<p><a href='{context['invitation_url']}' style='background-color: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;'>Accept Invitation</a></p>"
                )
            lines.append("<p>This invitation will expire in 7 days.</p>")

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
        from django.utils.dateparse import parse_datetime

        from events.models import Event
        from registrations.models import AttendanceRecord, Registration

        # Extract data
        meeting_id = str(payload.get('object', {}).get('id', ''))
        participant = payload.get('object', {}).get('participant', {})

        zoom_user_id = participant.get('user_id', '')
        user_name = participant.get('user_name', '')
        user_email = participant.get('email', '')
        participant_uuid = participant.get('id', '')  # Unique for this session
        join_time_str = participant.get('join_time')

        join_time = parse_datetime(join_time_str) if join_time_str else None

        logger.info(f"Participant joined meeting {meeting_id}: {user_email}")

        if not meeting_id or not join_time:
            logger.warning("Missing meeting_id or join_time in payload")
            return False

        # Try to find Event first
        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
            
            # Find Registration (if any)
            registration = None
            if user_email:
                registration = Registration.objects.filter(event=event, email__iexact=user_email, deleted_at__isnull=True).first()

            # Create Attendance Record
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
                    'matched_at': timezone.now() if registration else None,
                },
            )

            if registration:
                registration.update_attendance_summary()

            return True
        except Event.DoesNotExist:
            pass  # Try CourseSession next

        # Try to find CourseSession
        try:
            from learning.models import CourseEnrollment, CourseSession, CourseSessionAttendance

            session = CourseSession.objects.get(zoom_meeting_id=meeting_id)
            
            # Find Enrollment (if any)
            enrollment = None
            if user_email:
                enrollment = CourseEnrollment.objects.filter(
                    course=session.course,
                    user__email__iexact=user_email,
                    status='active'
                ).first()

            if enrollment:
                # Create or update attendance record
                attendance, created = CourseSessionAttendance.objects.get_or_create(
                    session=session,
                    enrollment=enrollment,
                    defaults={
                        'zoom_participant_id': participant_uuid,
                        'zoom_user_email': user_email,
                        'zoom_join_time': join_time,
                        'attendance_minutes': 0,
                    },
                )
                if not created:
                    # Update join time if new session (rejoin)
                    attendance.zoom_join_time = join_time
                    # Update participant UUID so 'left' event can find record
                    attendance.zoom_participant_id = participant_uuid
                    attendance.save(update_fields=['zoom_join_time', 'zoom_participant_id', 'updated_at'])

            logger.info(f"Session participant joined: {user_email} for session {session.uuid}")
            return True
        except Exception:
            pass

        logger.warning(f"Event/Session not found for Zoom meeting ID: {meeting_id}")
        return True  # Return True to acknowledge webhook receipt


    def _handle_participant_left(self, payload: dict) -> bool:
        """Handle participant leave event."""
        from django.utils.dateparse import parse_datetime

        from events.models import Event
        from registrations.models import AttendanceRecord

        meeting_id = str(payload.get('object', {}).get('id', ''))
        participant = payload.get('object', {}).get('participant', {})

        participant_uuid = participant.get('id', '')
        leave_time_str = participant.get('leave_time')

        leave_time = parse_datetime(leave_time_str) if leave_time_str else None

        logger.info(f"Participant left meeting {meeting_id}")

        if not meeting_id or not participant_uuid or not leave_time:
            return False

        # Try Event first
        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
            
            record = (
                AttendanceRecord.objects.filter(event=event, zoom_participant_id=participant_uuid, leave_time__isnull=True)
                .order_by('-join_time')
                .first()
            )

            if record:
                record.participant_left(leave_time=leave_time)
                logger.info(f"Closed attendance record for {record}")
            return True
        except Event.DoesNotExist:
            pass

        # Try CourseSession
        try:
            from learning.models import CourseSession, CourseSessionAttendance

            session = CourseSession.objects.get(zoom_meeting_id=meeting_id)
            
            # Find the attendance record and update leave time + duration
            attendance = CourseSessionAttendance.objects.filter(
                session=session,
                zoom_participant_id=participant_uuid
            ).first()

            if attendance and attendance.zoom_join_time:
                attendance.zoom_leave_time = leave_time
                # Calculate duration of THIS segment
                segment_duration = (leave_time - attendance.zoom_join_time).total_seconds() / 60
                
                # Accumulate minutes (don't overwrite)
                if segment_duration > 0:
                     attendance.attendance_minutes += int(segment_duration)
                
                # Calculate eligibility based on new total
                min_required = session.minimum_attendance_percent or 80
                attendance_percent = (attendance.attendance_minutes / session.duration_minutes * 100) if session.duration_minutes else 0
                attendance.is_eligible = attendance_percent >= min_required
                
                attendance.save(update_fields=[
                    'zoom_leave_time', 'attendance_minutes', 'is_eligible', 'updated_at'
                ])
                logger.info(f"Closed session attendance for session {session.uuid}")
            return True
        except Exception:
            pass

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
            records = attendance_records.filter(registration=reg)

            if records.exists():
                results['matched'] += 1
            else:
                results['unmatched'] += 1

            reg.update_attendance_summary()

            if reg.attendance_eligible:
                results['eligible'] += 1
            else:
                results['ineligible'] += 1

        return results

    def match_session_attendance(self, session) -> dict[str, Any]:
        """
        Match Zoom participant data to course session enrollments.

        Args:
            session: CourseSession to match attendance for

        Returns:
            Dict with match results
        """
        from learning.models import CourseSessionAttendance

        results = {'matched': 0, 'unmatched': 0, 'eligible': 0, 'ineligible': 0}

        # Get all attendance records for this session
        attendance_records = CourseSessionAttendance.objects.filter(
            session=session
        ).select_related('enrollment')

        for record in attendance_records:
            # Calculate eligibility based on attendance
            min_required = session.minimum_attendance_percent or 80
            attendance_percent = (record.attendance_minutes / session.duration_minutes * 100) if session.duration_minutes else 0

            is_eligible = attendance_percent >= min_required or record.is_manual_override
            record.is_eligible = is_eligible
            record.save(update_fields=['is_eligible', 'updated_at'])

            if record.zoom_user_email:
                results['matched'] += 1
            else:
                results['unmatched'] += 1

            if is_eligible:
                results['eligible'] += 1
            else:
                results['ineligible'] += 1

        return results


# Singleton instances
email_service = EmailService()
webhook_processor = WebhookProcessor()
attendance_matcher = AttendanceMatcher()
