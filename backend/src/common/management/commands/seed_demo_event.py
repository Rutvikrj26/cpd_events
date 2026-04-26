"""Spin up a single published event + test registration for P1 verification.

Used to verify the reminder lifecycle end-to-end without re-seeding the
whole demo set:

    python manage.py seed_demo_event --in 8m

After running, inspect:
- ``VideoRoom`` — should have a row for the event (proactively provisioned)
- ``ScheduledEmail`` — should have rows at every effective_reminder_offsets
  that haven't already passed
- The dispatched ``EmailLog`` will contain the join URL once
  ``dispatch_scheduled_emails`` runs (or once an offset matures).
"""

from __future__ import annotations

import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from events.models import Event
from registrations.models import Registration


_DURATION_RE = re.compile(r"^(\d+)([smhd])$")
_UNIT_TO_SECONDS = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}


def _parse_duration(value: str):
    m = _DURATION_RE.match(value.strip().lower())
    if not m:
        raise CommandError(f"Invalid --in value '{value}'. Use formats like 8m, 2h, 1d.")
    n, unit = int(m.group(1)), m.group(2)
    return timezone.timedelta(seconds=n * _UNIT_TO_SECONDS[unit])


class Command(BaseCommand):
    help = "Seed one published event + one confirmed registration for P1 verification."

    def add_arguments(self, parser):
        parser.add_argument(
            '--in', dest='start_in', default='8m',
            help='How far in the future the event starts (e.g. 8m, 2h, 1d). Default: 8m.',
        )
        parser.add_argument(
            '--learner-email', default='p1-verify@accredit.local',
            help='Email for the test registration.',
        )

    def handle(self, *args, **options):
        delta = _parse_duration(options['start_in'])
        starts_at = timezone.now() + delta
        learner_email = options['learner_email'].lower()

        User = get_user_model()
        with transaction.atomic():
            owner = User.objects.filter(is_superuser=True).first()
            if owner is None:
                owner = User.objects.first()
            if owner is None:
                raise CommandError("No users in DB — run `accredit local seed` first or create a user.")

            title = f"P1 Verification Event ({starts_at:%H:%M %Z})"
            slug = slugify(title)[:240] + '-' + str(int(timezone.now().timestamp()))
            event = Event.objects.create(
                owner=owner,
                title=title,
                slug=slug,
                description='Auto-generated event for verifying the P1 learner-flow reminder lifecycle.',
                short_description='P1 verification event.',
                event_type=Event.EventType.WEBINAR,
                format=Event.EventFormat.ONLINE,
                status=Event.Status.PUBLISHED,
                starts_at=starts_at,
                duration_minutes=60,
                price=Decimal('0.00'),
                video_settings={'enabled': True, 'recording_enabled': False, 'screen_share': True},
                cpd_enabled=False,
                certificates_enabled=False,
                badges_enabled=False,
                # Tighten the reminder schedule so it's easy to verify quickly.
                reminder_offsets_minutes=[10, 5, 2, 0],
            )

            # Ensure a learner group exists for the registrant if any.
            learner, _ = User.objects.get_or_create(
                email=learner_email,
                defaults={
                    'full_name': 'P1 Verifier',
                    'is_active': True,
                },
            )
            learner_group = Group.objects.filter(name='learner').first()
            if learner_group:
                learner.groups.add(learner_group)

            registration = Registration.objects.create(
                event=event,
                user=learner,
                email=learner_email,
                full_name='P1 Verifier',
                status=Registration.Status.CONFIRMED,
                payment_status=Registration.PaymentStatus.NA,
            )

            # Run the same enqueue path the registration confirmation task uses.
            from events.services import enqueue_event_reminders

            rows = enqueue_event_reminders(registration)

        from integrations.models import ScheduledEmail
        from conferencing.models import VideoRoom
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(Event)
        room = VideoRoom.objects.filter(content_type=ct, object_id=event.id).first()
        scheduled = list(ScheduledEmail.objects.filter(
            event=event, registration=registration
        ).order_by('send_at'))

        self.stdout.write(self.style.SUCCESS('P1 verification event seeded.'))
        self.stdout.write(f"  Event:        {event.title}")
        self.stdout.write(f"  starts_at:    {event.starts_at.isoformat()}")
        self.stdout.write(f"  uuid:         {event.uuid}")
        self.stdout.write(f"  Registration: {registration.email} (uuid={registration.uuid})")
        self.stdout.write(f"  VideoRoom:    {room.status if room else '—'}{' / ' + room.room_name if room else ''}")
        self.stdout.write(f"  Reminders:    {rows} scheduled (out of {len(event.effective_reminder_offsets_minutes)} offsets)")
        for s in scheduled:
            self.stdout.write(f"    - {s.send_at.isoformat()}  status={s.status}")
        self.stdout.write("")
        self.stdout.write("To dispatch matured rows manually:")
        self.stdout.write("  curl -X POST http://localhost:8000/api/common/cron/tick/")
