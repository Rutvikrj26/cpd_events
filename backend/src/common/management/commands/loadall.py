"""
Custom management command to load all fixtures in the project.

Usage:
    python manage.py loadall
"""

from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from billing.signals import create_subscription_for_new_user


class Command(BaseCommand):
    help = "Load all data fixtures in the project in a specific order."

    def handle(self, *args, **options):
        fixture_labels = self._discover_all_fixtures()
        
        if not fixture_labels:
            self.stdout.write(
                self.style.WARNING("No fixture files found in the project.")
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Found {len(fixture_labels)} fixtures. Loading them now...\n"
            )
        )
        
        # Display the fixtures that will be loaded
        for fixture in fixture_labels:
            self.stdout.write(f"  - {fixture}")
        self.stdout.write("")
        
        User = get_user_model()
        
        # Disconnect signal to prevent auto-creation of subscriptions during fixture loading
        # This prevents unique constraint errors when loading demo_billing.json
        self.stdout.write("Disconnecting subscription creation signal...")
        post_save.disconnect(create_subscription_for_new_user, sender=User)
        
        try:
            # Call the standard loaddata command with our list of fixtures
            call_command('loaddata', *fixture_labels)
            
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✅ Successfully loaded all fixtures!"
                )
            )
        finally:
            # Reconnect signal
            self.stdout.write("Reconnecting subscription creation signal...")
            post_save.connect(create_subscription_for_new_user, sender=User)

    def _discover_all_fixtures(self):
        """Discover all fixture files in the project."""
        fixtures = []
        base_dir = Path(settings.BASE_DIR)
        
        # Search for all .json fixture files
        for fixture_path in base_dir.rglob('fixtures/*.json'):
            # Get the fixture name (filename without extension)
            fixture_name = fixture_path.stem
            
            # Avoid duplicates
            if fixture_name not in fixtures:
                fixtures.append(fixture_name)
        
        # Sort fixtures to ensure consistent loading order
        # Load in a logical order: users -> contacts -> events -> registrations, etc.
        priority_order = [
            'demo_users',
            'demo_contacts',
            'demo_tags',
            'demo_events',
            'demo_sessions',
            'demo_session_attendance',
            'demo_status_variations',
            'demo_registrations',
            'demo_custom_fields',
            'demo_attendance',
            'demo_promos',
            'demo_usage',
            'demo_billing',
            'demo_financial',
            'demo_certificates',
            'demo_badges',
            'demo_audit',
            'demo_feedback',
            'demo_learning',
            'demo_hybrid_courses',
            'demo_progress',
            'demo_assignments',
            'demo_announcements',
            'demo_cpd',
            'demo_emails',
            'demo_zoom',
        ]
        
        # Sort: priority fixtures first, then alphabetically
        sorted_fixtures = []
        for priority_fixture in priority_order:
            if priority_fixture in fixtures:
                sorted_fixtures.append(priority_fixture)
                fixtures.remove(priority_fixture)
        
        # Add remaining fixtures alphabetically
        sorted_fixtures.extend(sorted(fixtures))
        
        return sorted_fixtures
