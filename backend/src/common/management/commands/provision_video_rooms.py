"""Backfill video rooms for events that should have them but don't.

Use cases:
- A LiveKit outage caused initial provisioning to fail (room rows exist with
  status=ERROR), and the queue retries are exhausted.
- Older published events were created before proactive provisioning was
  wired up.

Idempotent: safe to run repeatedly. Skips events that already have a healthy
VideoRoom row.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from conferencing.models import VideoRoom
from conferencing.tasks import create_video_room_for_object
from events.models import Event


class Command(BaseCommand):
    help = "Provision missing or errored video rooms for upcoming/live events with video enabled."

    def add_arguments(self, parser):
        parser.add_argument(
            '--include-completed',
            action='store_true',
            help='Also provision rooms for completed events (e.g., for re-watch).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be done without enqueuing.',
        )

    def handle(self, *args, **options):
        statuses = [Event.Status.PUBLISHED, Event.Status.LIVE]
        if options['include_completed']:
            statuses.append(Event.Status.COMPLETED)

        ct = ContentType.objects.get_for_model(Event)
        events = Event.objects.filter(status__in=statuses, deleted_at__isnull=True)

        scanned = 0
        scheduled = 0
        skipped = 0
        for event in events.iterator():
            scanned += 1
            video_settings = event.video_settings or {}
            if not (isinstance(video_settings, dict) and video_settings.get('enabled')):
                skipped += 1
                continue
            healthy = VideoRoom.objects.filter(
                content_type=ct, object_id=event.id
            ).exclude(status=VideoRoom.Status.ERROR).exists()
            if healthy:
                skipped += 1
                continue
            self.stdout.write(f"  → Provisioning room for event {event.uuid} ({event.title})")
            if not options['dry_run']:
                create_video_room_for_object.delay(ct.id, event.id)
            scheduled += 1

        self.stdout.write(self.style.SUCCESS(
            f"Scanned {scanned}; scheduled {scheduled}; skipped {skipped}."
        ))
