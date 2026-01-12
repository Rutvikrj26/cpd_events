import os

import pytest
from django.conf import settings
from django.core.mail import EmailMessage, get_connection

# Path to .secrets file in project root
SECRETS_FILE = settings.BASE_DIR.parent.parent / '.secrets'


def load_secrets():
    """Load secrets from .secrets file into a dict."""
    secrets = {}
    if SECRETS_FILE.exists():
        with open(SECRETS_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    secrets[key.strip()] = value.strip()
    return secrets


@pytest.mark.live_email
def test_send_live_email_via_brevo():
    """
    Attempt to send a real email using credentials from .secrets.
    This test is skipped if credentials are missing.
    """
    secrets = load_secrets()

    if os.environ.get('RUN_LIVE_EMAIL_TESTS') != '1':
        pytest.skip("Set RUN_LIVE_EMAIL_TESTS=1 to run live email test.")

    # Check for required credentials (mapping typical Brevo/SMTP keys)
    # User mentioned Brevo, which usually uses:
    # Host: smtp-relay.brevo.com
    # Port: 587

    host = (
        secrets.get('SMTP_SERVER') or secrets.get('BREVO_SMTP_SERVER') or os.environ.get('SMTP_SERVER', 'smtp-relay.brevo.com')
    )
    port = int(secrets.get('SMTP_PORT') or secrets.get('BREVO_SMTP_PORT') or os.environ.get('SMTP_PORT', '587'))
    login = secrets.get('SMTP_LOGIN') or secrets.get('BREVO_SMTP_LOGIN') or os.environ.get('SMTP_LOGIN')
    password = secrets.get('SMTP_PASSWORD') or secrets.get('BREVO_SMTP_PASSWORD') or os.environ.get('SMTP_PASSWORD')

    if not login or not password:
        pytest.skip("Skipping live email test: SMTP credentials not found in .secrets or environment.")

    print(f"\nAttempting to send live email via {host}:{port} as {login}...")

    # Configure connection manually
    connection = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=host,
        port=port,
        username=login,
        password=password,
        use_tls=True,
        timeout=10,
    )

    email = EmailMessage(
        subject='Accredit Test',
        body='This is a test email from the Accredit automated test suite.',
        from_email='info@accredit.store',
        to=['rutvikrj26@gmail.com'],
        connection=connection,
    )

    try:
        sent_count = email.send(fail_silently=False)
        assert sent_count == 1
        print("Live email sent successfully!")
    except Exception as e:
        pytest.fail(f"Failed to send live email: {e}")
