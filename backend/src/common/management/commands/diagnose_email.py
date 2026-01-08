from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import get_connection
from integrations.services import email_service

class Command(BaseCommand):
    help = 'Diagnose email configuration and attempt to send a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='test@example.com',
            help='Email address to send test email to'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Email Configuration Diagnostics'))
        
        # 1. Print Settings
        self.stdout.write(f"EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'Not Set')}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not Set')}")
        self.stdout.write(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not Set')}")
        self.stdout.write(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'Not Set')}")
        self.stdout.write(f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'Not Set')}")
        
        recipient = options['email']
        self.stdout.write(f"\nAttempting to send test email to: {recipient}")

        # 2. Test Connection
        try:
            connection = get_connection()
            self.stdout.write("Connection object created successfully.")
        except Exception as e:
             self.stdout.write(self.style.ERROR(f"Failed to create connection: {e}"))
             return

        # 3. Send Email via Service
        try:
            # We use a simple context and a template that is likely to exist or fallback
            # 'verification' usually exists if we have user flows
            # But let's use the simplest one or the direct _send method if we want to be raw
            # The service has a fallback for missing templates, so let's try a 'test' template
            
            success = email_service.send_email(
                template='test_diagnostic', # This will trigger the fallback simple HTML
                recipient=recipient,
                context={'user_name': 'Test User', 'message': 'This is a diagnostic email.'},
                subject='CPD Events Email Diagnostic'
            )
            
            if success:
                self.stdout.write(self.style.SUCCESS(f"Email successfully passed to backend for {recipient}"))
                self.stdout.write("Check your console (if in dev) or email inbox (if in prod).")
            else:
                self.stdout.write(self.style.ERROR("EmailService returned False."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Exception during sending: {e}"))
