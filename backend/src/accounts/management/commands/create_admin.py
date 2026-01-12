"""
Custom management command to create a superuser non-interactively.
Usage: python manage.py create_admin --email=admin@example.com --password=secret
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a superuser account non-interactively'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Admin email address')
        parser.add_argument('--password', type=str, required=True, help='Admin password')
        parser.add_argument('--name', type=str, default='Admin', help='Full name (default: Admin)')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options['email']
        password = options['password']
        full_name = options['name']

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'User {email} already exists. Updating to superuser...'))
            user = User.objects.get(email=email)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.email_verified = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Updated {email} as superuser'))
        else:
            User.objects.create_superuser(
                email=email,
                password=password,
                full_name=full_name,
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created superuser: {email}'))
