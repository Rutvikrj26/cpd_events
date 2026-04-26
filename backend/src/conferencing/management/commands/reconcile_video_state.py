"""
Run the conferencing stale-state reconciler manually.

Usage:
    python manage.py reconcile_video_state
"""

from django.core.management.base import BaseCommand

from conferencing.reconciler import reconcile_stale_video_state


class Command(BaseCommand):
    help = 'Scrub VideoRoom / VideoRecording rows whose state is wedged.'

    def handle(self, *args, **options):
        result = reconcile_stale_video_state()
        self.stdout.write(self.style.SUCCESS(
            f"reconciled rooms={result['rooms']} recordings={result['recordings']}"
        ))
