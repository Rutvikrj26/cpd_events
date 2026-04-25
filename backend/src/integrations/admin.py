"""Admin for the integrations app, with debugging surface for emails.

Two staff-only utilities are exposed beyond the default list views:

1. **Preview an email template** — render any registered template against
   a fixture context, with optional event/registration overrides for richer
   preview data. Useful for "what does the reminder actually look like?"
   without sending mail.

2. **Send a test of an EmailLog** — re-render and dispatch the log row to
   the staff user's own email. Useful for "did the learner actually get
   this?" without leaving the admin.
"""

from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .models import EmailLog, ScheduledEmail


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'email_type', 'status', 'sent_at', 'event', 'admin_actions')
    list_filter = ('email_type', 'status')
    search_fields = ('recipient_email', 'subject')
    ordering = ('-created_at',)
    actions = ['resend_to_self']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'preview/',
                self.admin_site.admin_view(self.preview_view),
                name='integrations_emaillog_preview',
            ),
        ]
        return custom + urls

    @admin.display(description='Actions')
    def admin_actions(self, obj):
        return format_html(
            '<a href="{}?log_id={}" class="button">Preview</a>',
            reverse('admin:integrations_emaillog_preview'), obj.id,
        )

    @admin.action(description="Resend a copy to my staff email")
    def resend_to_self(self, request, queryset):
        from integrations.services import email_service

        recipient = getattr(request.user, 'email', '') or ''
        if not recipient:
            self.message_user(request, "Your staff user has no email address.", messages.ERROR)
            return
        sent = 0
        for log in queryset:
            test_log = EmailLog.objects.create(
                recipient_email=recipient,
                recipient_name=getattr(request.user, 'full_name', '') or 'Admin',
                recipient_user=request.user,
                email_type=log.email_type,
                subject=f"[TEST] {log.subject}",
                event=log.event,
                registration=log.registration,
                certificate=log.certificate,
            )
            ctx = self._fixture_context_for(log)
            attachments = self._attachments_for(log)
            email_service.send_log(test_log, context=ctx, attachments=attachments)
            sent += 1
        self.message_user(request, f"Sent {sent} test email(s) to {recipient}.", messages.SUCCESS)

    def preview_view(self, request):
        """Render any template against fixture context. Read-only — does not send."""
        from django.template.loader import render_to_string

        from integrations.services import email_service

        log_id = request.GET.get('log_id')
        template = request.GET.get('template') or ''
        log = None
        if log_id:
            log = EmailLog.objects.filter(id=log_id).first()
            if log and not template:
                template = log.email_type

        ctx = self._fixture_context_for(log) if log else self._default_fixture_context(template)
        rendered = ''
        error = ''
        if template:
            template_path = email_service.TEMPLATES.get(template)
            if not template_path:
                error = f"No template registered for key '{template}'."
            else:
                try:
                    rendered = render_to_string(template_path, ctx)
                except Exception as e:
                    error = f"Render error: {e}"
                    rendered = email_service._build_simple_html(template, ctx)

        return render(
            request,
            'admin/integrations/email_preview.html',
            {
                'title': 'Email preview',
                'template_keys': sorted(email_service.TEMPLATES.keys()),
                'selected_template': template,
                'context_json': ctx,
                'rendered': rendered,
                'error': error,
                'log': log,
            },
        )

    _COURSE_EMAIL_TYPES = {'course_enrolled', 'enrollment_confirmation', 'module_released', 'course_completed'}

    def _fixture_context_for(self, log) -> dict:
        ctx = {
            'user_name': log.recipient_name or 'Test User',
            'recipient_email': log.recipient_email,
        }
        # Course emails don't have an event/registration FK on EmailLog, so
        # seed plausible course-shaped defaults from the subject so the
        # preview renders something useful.
        if log.email_type in self._COURSE_EMAIL_TYPES:
            # Subject patterns: "You're enrolled in <title>", "Course complete: <title>",
            # "New module unlocked: <title>" — strip the prefix to recover the title.
            subj = log.subject or ''
            for prefix in ("You're enrolled in ", "Course complete: ", "New module unlocked: "):
                if subj.startswith(prefix):
                    derived_title = subj[len(prefix):]
                    break
            else:
                derived_title = subj
            ctx.update({
                'course_title': derived_title or 'Course Title (Preview)',
                'module_title': derived_title or 'Module Title (Preview)',
                'instructor_name': 'Sample Instructor',
                'module_count': 5,
                'estimated_hours': '6',
                'first_module_title': 'Sample First Module',
                'upcoming_session_count': 2,
                'course_url': 'https://example.test/learn/preview',
                'module_url': 'https://example.test/learn/preview#module-1',
                'module_description': 'Preview module description.',
                'cpd_credits': '1.0',
                'cpd_type': 'CME',
                'progress_percent': 60,
                'final_score': 92,
                'completed_at': 'April 25, 2026',
                'certificate_url': 'https://example.test/certificates/preview',
            })
        if log.event:
            ctx.update({
                'event_title': log.event.title,
                'event_date': log.event.starts_at.strftime('%B %d, %Y at %I:%M %p'),
                'event_timezone': log.event.timezone,
                'duration_minutes': log.event.duration_minutes,
            })
            try:
                from events.services import _reminder_context, build_event_join_url
                from integrations.calendar import google_calendar_url, outlook_calendar_url

                if log.registration:
                    ctx.update(_reminder_context(log.event, log.registration))
                else:
                    ctx['join_url'] = build_event_join_url(log.event)
                    description = (log.event.short_description or '')
                    ctx['add_to_google_url'] = google_calendar_url(
                        summary=log.event.title,
                        starts_at=log.event.starts_at,
                        ends_at=log.event.ends_at,
                        description=description,
                        location=log.event.location or ctx['join_url'],
                    )
                    ctx['add_to_outlook_url'] = outlook_calendar_url(
                        summary=log.event.title,
                        starts_at=log.event.starts_at,
                        ends_at=log.event.ends_at,
                        description=description,
                        location=log.event.location or ctx['join_url'],
                    )
            except Exception:
                pass
        if log.certificate:
            ctx['certificate_url'] = getattr(log.certificate, 'verification_url', '') or ''
            ctx['short_code'] = getattr(log.certificate, 'short_code', '') or ''
            ctx['verification_url'] = ctx['certificate_url']
        return ctx

    def _attachments_for(self, log):
        if not log.event or log.email_type not in {
            'event_reminder', 'registration_confirm', 'registration_confirmation',
            'waitlist_promotion', 'event_cancelled', 'invitation',
        }:
            return None
        try:
            from events.services import build_event_ics

            ics = build_event_ics(log.event, attendee_email=log.recipient_email, attendee_name=log.recipient_name)
        except Exception:
            return None
        method = 'CANCEL' if log.event.status == 'cancelled' else 'PUBLISH'
        return [('event.ics', ics, f'text/calendar; method={method}; charset=utf-8')]

    def _default_fixture_context(self, template: str) -> dict:
        return {
            'user_name': 'Test Recipient',
            'event_title': 'Sample Event Title',
            'event_date': 'April 25, 2026 at 10:00 AM',
            'event_timezone': 'UTC',
            'duration_minutes': 60,
            'join_url': 'https://example.test/events/preview/lobby',
            'add_to_google_url': 'https://calendar.google.com/calendar/render?action=TEMPLATE&text=Sample',
            'add_to_outlook_url': 'https://outlook.live.com/calendar/0/deeplink/compose?path=/calendar/action/compose',
            'certificate_url': 'https://example.test/certificates/preview',
            'verification_url': 'https://example.test/verify/preview',
            'short_code': 'ABCD-1234',
            'badge_name': 'Sample Badge',
            'badge_url': 'https://example.test/badges/preview.png',
            'inviter_name': 'Sample Inviter',
            'invitation_url': 'https://example.test/invite/preview',
        }


@admin.register(ScheduledEmail)
class ScheduledEmailAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'template_key', 'send_at', 'status', 'batch_key')
    list_filter = ('status', 'template_key')
    search_fields = ('recipient_email', 'subject', 'batch_key')
    ordering = ('send_at',)
    raw_id_fields = ('recipient_user', 'event', 'registration', 'email_log')
    actions = ['dispatch_now']

    @admin.action(description="Dispatch now (ignore send_at)")
    def dispatch_now(self, request, queryset):
        sent = 0
        for s in queryset.filter(status=ScheduledEmail.Status.PENDING):
            try:
                s.dispatch()
                sent += 1
            except Exception as e:
                self.message_user(request, f"Failed to dispatch #{s.id}: {e}", messages.ERROR)
        self.message_user(request, f"Dispatched {sent} scheduled email(s).", messages.SUCCESS)
