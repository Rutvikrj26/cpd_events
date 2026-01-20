"""
Test Sentry integration.

Usage: python manage.py test_sentry
"""

from django.core.management.base import BaseCommand
import sentry_sdk


class Command(BaseCommand):
    help = "Test Sentry error tracking integration"

    def handle(self, *args, **kwargs):
        self.stdout.write("Testing Sentry integration...")
        self.stdout.write("This will send a test error to Sentry. Check your Sentry dashboard at https://sentry.io/\n")

        try:
            # Trigger a test error
            raise Exception("This is a test error from Django management command - Sentry integration test")
        except Exception as e:
            sentry_sdk.capture_exception(e)
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Test error sent to Sentry: {e}\n\n"
                    "If you see this error in your Sentry dashboard, "
                    "Sentry is working correctly!\n\n"
                    "NOTE: If SENTRY_DSN is not configured, this will do nothing."
                )
            )
